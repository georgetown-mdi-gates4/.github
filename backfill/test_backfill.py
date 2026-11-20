"""Tests for backfill.py. Each test puts a fake `gh` on PATH. The fake
answers each command from a table of canned replies and logs every call
it gets, so a test checks the printed plan, the exit code, and which
write calls were made.

Run: python3 -m unittest discover -s backfill -v
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "backfill.py")
with open(os.path.join(HERE, "config.json")) as f:
    CONFIG = json.load(f)
BRANCH = CONFIG["branch"]
ORG = "acme"
LIST = f"repo list {ORG} --limit {CONFIG['repo_limit']} --json name,isFork,isArchived,isEmpty,defaultBranchRef"

# The fake gh. Replies are keyed by the arguments joined with spaces.
# An unknown command fails, so a test also catches a call it did not expect.
FAKE_GH = r'''#!/usr/bin/env python3
import json, os, sys
d = os.environ["FAKE_GH_DIR"]
args = sys.argv[1:]
call = {"args": args}
if "--input" in args:
    call["stdin"] = sys.stdin.read()
with open(os.path.join(d, "calls.jsonl"), "a") as f:
    f.write(json.dumps(call) + "\n")
with open(os.path.join(d, "replies.json")) as f:
    reply = json.load(f).get(" ".join(args))
if reply is None:
    sys.stderr.write("fake gh: no reply for: " + " ".join(args) + "\n")
    sys.exit(1)
sys.stdout.write(reply.get("stdout", ""))
sys.stderr.write(reply.get("stderr", ""))
sys.exit(reply.get("code", 0))
'''


def ok(data):
    return {"stdout": json.dumps(data)}


def fail(stderr):
    return {"code": 1, "stderr": stderr}


def repo(name, fork=False, archived=False, empty=False, base="main"):
    return {"name": name, "isFork": fork, "isArchived": archived, "isEmpty": empty,
            "defaultBranchRef": {"name": base}}


def pulls_key(name):
    return f"api repos/{ORG}/{name}/pulls?state=open&head={ORG}:{BRANCH}"


def contents_key(name):
    return f"api repos/{ORG}/{name}/contents"


def readable(name, files, open_prs=()):
    """Replies for a repo whose root holds `files`."""
    return {
        pulls_key(name): ok([{"number": n} for n in open_prs]),
        contents_key(name): ok([{"name": f, "type": "file"} for f in files]),
    }


def writes(name, missing, base="main", sha="abc123"):
    """Replies for the write calls --apply makes on one repo."""
    out = {
        f"api repos/{ORG}/{name}/git/ref/heads/{base}": ok({"object": {"sha": sha}}),
        f"api -X POST repos/{ORG}/{name}/git/refs --input -": ok({}),
        f"api -X POST repos/{ORG}/{name}/pulls --input -":
            ok({"html_url": f"https://github.com/{ORG}/{name}/pull/1"}),
    }
    for path in missing:
        out[f"api -X PUT repos/{ORG}/{name}/contents/{path} --input -"] = ok({})
    return out


def template(path, **subs):
    with open(os.path.join(HERE, CONFIG["files"][path]["template"])) as f:
        return Template(f.read()).safe_substitute(**subs)


class BackfillTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        gh = os.path.join(self.dir, "gh")
        with open(gh, "w") as f:
            f.write(FAKE_GH)
        os.chmod(gh, 0o755)

    def run_script(self, repos, replies, *flags):
        replies = dict(replies)
        replies.setdefault(LIST, ok(repos))
        with open(os.path.join(self.dir, "replies.json"), "w") as f:
            json.dump(replies, f)
        env = dict(os.environ, FAKE_GH_DIR=self.dir,
                   PATH=self.dir + os.pathsep + os.environ["PATH"])
        p = subprocess.run([sys.executable, SCRIPT, ORG, *flags],
                           capture_output=True, text=True, env=env)
        return p.stdout.splitlines(), p.returncode

    def calls(self):
        path = os.path.join(self.dir, "calls.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(line) for line in f]

    def write_calls(self):
        return [c for c in self.calls() if "-X" in c["args"]]

    def test_missing_both(self):
        out = self.run_script([repo("both")], readable("both", ["src"]))
        self.assertEqual(out, ([f"{ORG}/both: missing README.md, .gitignore"], 0))

    def test_missing_readme_only(self):
        out = self.run_script([repo("noreadme")], readable("noreadme", [".gitignore"]))
        self.assertEqual(out, ([f"{ORG}/noreadme: missing README.md"], 0))

    def test_readme_any_case_and_extension_counts(self):
        repos = [repo("lower"), repo("plain"), repo("rst")]
        replies = {**readable("lower", ["readme.MD", ".gitignore"]),
                   **readable("plain", ["README", ".gitignore"]),
                   **readable("rst", ["ReadMe.rst", ".gitignore"])}
        self.assertEqual(self.run_script(repos, replies), ([
            f"{ORG}/lower: ok",
            f"{ORG}/plain: ok",
            f"{ORG}/rst: ok",
        ], 0))

    def test_readme_lookalike_does_not_count(self):
        out = self.run_script([repo("r")], readable("r", ["README-old.md", ".gitignore"]))
        self.assertEqual(out, ([f"{ORG}/r: missing README.md"], 0))

    def test_readme_folder_does_not_count(self):
        replies = readable("r", [".gitignore"])
        replies[contents_key("r")] = ok([{"name": "readme", "type": "dir"},
                                         {"name": ".gitignore", "type": "file"}])
        self.assertEqual(self.run_script([repo("r")], replies), ([f"{ORG}/r: missing README.md"], 0))

    def test_gitignore_name_is_exact_case(self):
        out = self.run_script([repo("g")], readable("g", ["README.md", ".GitIgnore"]))
        self.assertEqual(out, ([f"{ORG}/g: missing .gitignore"], 0))

    def test_complete_repo(self):
        out = self.run_script([repo("done")], readable("done", ["README.md", ".gitignore"]))
        self.assertEqual(out, ([f"{ORG}/done: ok"], 0))

    def test_skips_fork_archived_empty_with_no_calls(self):
        repos = [repo("forked", fork=True), repo("old", archived=True), repo("blank", empty=True)]
        self.assertEqual(self.run_script(repos, {}), ([
            f"{ORG}/forked: skipped (fork)",
            f"{ORG}/old: skipped (archived)",
            f"{ORG}/blank: skipped (empty)",
        ], 0))
        self.assertEqual([c["args"] for c in self.calls()], [LIST.split(" ")])

    def test_skips_repo_with_open_backfill_pr(self):
        out = self.run_script([repo("haspr")], readable("haspr", ["src"], open_prs=[7]))
        self.assertEqual(out, ([f"{ORG}/haspr: skipped (open backfill PR #7)"], 0))

    def test_gh_error_on_one_repo(self):
        repos = [repo("broken"), repo("both")]
        replies = {pulls_key("broken"): ok([]),
                   contents_key("broken"): fail("gh: Server Error (HTTP 500)\n"),
                   **readable("both", ["src"])}
        self.assertEqual(self.run_script(repos, replies), ([
            f"{ORG}/broken: error (gh {contents_key('broken')}: gh: Server Error (HTTP 500))",
            f"{ORG}/both: missing README.md, .gitignore",
        ], 1))

    def test_404_on_root_listing_is_an_error(self):
        replies = {pulls_key("gone"): ok([]),
                   contents_key("gone"): fail("gh: Not Found (HTTP 404)\n")}
        self.assertEqual(self.run_script([repo("gone")], replies), ([
            f"{ORG}/gone: error (gh {contents_key('gone')}: gh: Not Found (HTTP 404))",
        ], 1))

    def test_gh_error_on_pr_check(self):
        replies = {pulls_key("x"): fail("gh: Bad credentials (HTTP 401)\n")}
        self.assertEqual(self.run_script([repo("x")], replies), ([
            f"{ORG}/x: error (gh {pulls_key('x')}: gh: Bad credentials (HTTP 401))",
        ], 1))

    def test_repo_list_error(self):
        out = self.run_script([], {LIST: fail("gh: Not Found (HTTP 404)\n")})
        self.assertEqual(out, ([f"{ORG}: error (gh {LIST}: gh: Not Found (HTTP 404))"], 1))

    def test_dry_run_makes_no_write_call(self):
        repos = [repo("both"), repo("noreadme")]
        replies = {**readable("both", ["src"]), **readable("noreadme", [".gitignore"]),
                   **writes("both", ["README.md", ".gitignore"]), **writes("noreadme", ["README.md"])}
        self.assertEqual(self.run_script(repos, replies), ([
            f"{ORG}/both: missing README.md, .gitignore",
            f"{ORG}/noreadme: missing README.md",
        ], 0))
        self.assertEqual(self.write_calls(), [])
        self.assertTrue(all(not c["args"][1].endswith("/git/ref/heads/main") for c in self.calls()))

    def test_apply_opens_one_pr_per_repo_with_only_missing_files(self):
        repos = [repo("both"), repo("noreadme", base="master"), repo("done"),
                 repo("forked", fork=True)]
        replies = {**readable("both", ["src"]), **readable("noreadme", [".gitignore"]),
                   **readable("done", ["README.md", ".gitignore"]),
                   **writes("both", ["README.md", ".gitignore"]),
                   **writes("noreadme", ["README.md"], base="master", sha="def456")}
        self.assertEqual(self.run_script(repos, replies, "--apply"), ([
            f"{ORG}/both: missing README.md, .gitignore",
            f"{ORG}/both: opened https://github.com/{ORG}/both/pull/1",
            f"{ORG}/noreadme: missing README.md",
            f"{ORG}/noreadme: opened https://github.com/{ORG}/noreadme/pull/1",
            f"{ORG}/done: ok",
            f"{ORG}/forked: skipped (fork)",
        ], 0))
        got = [(c["args"][2], c["args"][3], json.loads(c["stdin"])) for c in self.write_calls()]
        self.assertEqual([(m, path) for m, path, _ in got], [
            ("POST", f"repos/{ORG}/both/git/refs"),
            ("PUT", f"repos/{ORG}/both/contents/README.md"),
            ("PUT", f"repos/{ORG}/both/contents/.gitignore"),
            ("POST", f"repos/{ORG}/both/pulls"),
            ("POST", f"repos/{ORG}/noreadme/git/refs"),
            ("PUT", f"repos/{ORG}/noreadme/contents/README.md"),
            ("POST", f"repos/{ORG}/noreadme/pulls"),
        ])
        bodies = [b for _, _, b in got]
        self.assertEqual(bodies[0], {"ref": f"refs/heads/{BRANCH}", "sha": "abc123"})
        self.assertEqual(bodies[3]["base"], "main")
        # noreadme's default branch is master: the ref read, the branch-from
        # SHA and the PR base must all follow it.
        self.assertIn(["api", f"repos/{ORG}/noreadme/git/ref/heads/master"],
                      [c["args"] for c in self.calls()])
        self.assertEqual(bodies[4], {"ref": f"refs/heads/{BRANCH}", "sha": "def456"})
        self.assertEqual(bodies[1]["branch"], BRANCH)
        self.assertEqual(base64.b64decode(bodies[1]["content"]).decode(),
                         template("README.md", repo="both"))
        self.assertEqual(base64.b64decode(bodies[2]["content"]).decode(), template(".gitignore"))
        pr = bodies[6]
        self.assertEqual((pr["head"], pr["base"], pr["title"]), (BRANCH, "master", CONFIG["pr_title"]))
        self.assertIn("`README.md`", pr["body"])
        self.assertNotIn("`.gitignore`", pr["body"])
        self.assertIn(f"https://github.com/{ORG}/.github/blob/main/CONTRIBUTING.md", pr["body"])

    def test_apply_write_failure_is_an_error(self):
        replies = {**readable("both", ["src"]), **writes("both", ["README.md", ".gitignore"])}
        replies[f"api -X POST repos/{ORG}/both/git/refs --input -"] = fail(
            "gh: Reference already exists (HTTP 422)\n")
        lines, code = self.run_script([repo("both")], replies, "--apply")
        self.assertEqual(lines, [
            f"{ORG}/both: missing README.md, .gitignore",
            f"{ORG}/both: error (gh api -X POST repos/{ORG}/both/git/refs --input -: "
            "gh: Reference already exists (HTTP 422))",
        ])
        self.assertEqual(code, 1)
        self.assertEqual(len(self.write_calls()), 1)

    def test_templates_hold_the_standard(self):
        ignore = template(".gitignore").splitlines()
        for line in [".env", "/data/", "/index/", "build/", "dist/", "__pycache__/",
                     "node_modules/", ".venv/"]:
            self.assertIn(line, ignore)
        readme = template("README.md").splitlines()
        self.assertIn("## How to run", readme)
        self.assertIn("## Who owns this", readme)

    @unittest.skipIf(shutil.which("git") is None, "git is not on PATH")
    def test_gitignore_template_ignores_only_root_data_and_index(self):
        subprocess.run(["git", "init", "-q", self.dir], check=True)
        with open(os.path.join(self.dir, ".gitignore"), "w") as f:
            f.write(template(".gitignore"))
        cases = {"data/x.csv": True, "index/v.npy": True, ".env": True,
                 "tests/fixtures/data/small.csv": False, "src/pkg/data/loader.py": False,
                 "src/pkg/index/__init__.py": False}
        for path, ignored in cases.items():
            p = subprocess.run(["git", "-C", self.dir, "check-ignore", "-q", "--no-index", path])
            self.assertEqual(p.returncode == 0, ignored, path)


if __name__ == "__main__":
    unittest.main()

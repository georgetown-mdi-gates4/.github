"""Tests for scan.sh. Each test builds a folder in a temp dir, runs the
scan on it, and checks the exit code and the printed result.

The fake token is built at run time from pieces, so this repo never holds
a string that looks like a real secret (the check scans this repo too).

Run: python3 -m unittest discover -s secret-scan -v
Set REQUIRE_GITLEAKS=1 to fail, not skip, when gitleaks is not on PATH.
"""
import hashlib
import io
import os
import re
import secrets
import shutil
import string
import subprocess
import tarfile
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "scan.sh")
REPO = os.path.dirname(HERE)
WORKFLOW = os.path.join(REPO, ".github", "workflows", "data-check.yml")
PIN_FILE = os.path.join(HERE, "gitleaks-release.env")
CONFIG = os.path.join(HERE, "gitleaks.toml")
DOCS = os.path.join(REPO, "README.md")


def release_pin():
    """gitleaks-release.env as a dict of its KEY=value lines."""
    with open(PIN_FILE) as f:
        return dict(l.strip().split("=", 1) for l in f if l.strip() and not l.startswith("#"))


def fake_github_token():
    body = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))
    return "_".join(["ghp", body])


def write_token(folder, suffix="", name="config.py"):
    token = fake_github_token()
    path = os.path.join(folder, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(f'TOKEN = "{token}"{suffix}\n')
    return token


def write(folder, name, text):
    with open(os.path.join(folder, name), "w") as f:
        f.write(text)


def workflow_job():
    """The data-check job as (header lines, list of steps). Each part is
    its list of lines, without comment lines and blank lines."""
    with open(WORKFLOW) as f:
        lines = [l for l in f.read().split("\n") if l.strip() and not l.strip().startswith("#")]
    start = lines.index("  data-check:")
    at = lines.index("    steps:", start)
    steps = []
    for line in lines[at + 1:]:
        if line.startswith("      - "):
            steps.append([])
        steps[-1].append(line)
    return lines[start:at + 1], steps


def workflow_step(name):
    found = [s for s in workflow_job()[1] if s[0] == f"      - name: {name}"]
    assert len(found) == 1, f"want one '{name}' step in the workflow"
    return found[0]


def workflow_run_command(name):
    return workflow_step(name)[-1].split("run: ", 1)[1]


def token_file_bytes():
    return f'TOKEN = "{fake_github_token()}"\n'.encode()


def run(path, cwd=None):
    p = subprocess.run(["sh", SCRIPT, path], capture_output=True, text=True, cwd=cwd)
    return p.returncode, p.stdout + p.stderr


# Pins the whole job header and the two secret-scan steps, every key and
# value, so no key such as "if: false" or "continue-on-error: true" can
# switch the scan off.
class WorkflowPinTest(unittest.TestCase):
    def test_job_header_is_pinned(self):
        self.assertEqual(workflow_job()[0], [
            "  data-check:",
            "    runs-on: ubuntu-latest",
            "    steps:",
        ])

    def test_install_step_is_pinned(self):
        self.assertEqual(workflow_step("Install gitleaks"), [
            "      - name: Install gitleaks",
            "        if: ${{ !cancelled() }}",
            '        run: sh .org-check/secret-scan/install.sh "$RUNNER_TEMP/gitleaks" >> "$GITHUB_PATH"',
        ])

    def test_scan_step_is_pinned(self):
        self.assertEqual(workflow_step("Secret scan"), [
            "      - name: Secret scan",
            "        if: ${{ !cancelled() }}",
            "        run: sh .org-check/secret-scan/scan.sh target",
        ])

    # The scan runs after the data check, as the ticket asks.
    def test_data_check_runs_before_the_secret_scan(self):
        firsts = [s[0] for s in workflow_job()[1]]
        order = [firsts.index("      - run: python3 .org-check/data-check/check.py target"),
                 firsts.index("      - name: Install gitleaks"),
                 firsts.index("      - name: Secret scan")]
        self.assertEqual(order, sorted(order))


# Any edit to gitleaks.toml, or a version bump in one place only, fails
# here, so a weaker config cannot pass review unnoticed.
class PinTest(unittest.TestCase):
    def test_config_matches_its_sha256_pin(self):
        with open(CONFIG, "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(),
                             release_pin()["GITLEAKS_CONFIG_SHA256"])

    def test_version_is_the_same_everywhere(self):
        version = release_pin()["GITLEAKS_VERSION"]
        with open(CONFIG) as f:
            self.assertEqual(re.findall(r"/blob/v([0-9.]+)/config/", f.read()), [version])
        with open(DOCS) as f:
            named = re.findall(r"\b\d+\.\d+\.\d+\b", f.read())
        self.assertTrue(named, "the docs name no gitleaks version")
        self.assertEqual(set(named), {version})


@unittest.skipUnless(shutil.which("gitleaks") or os.environ.get("REQUIRE_GITLEAKS") == "1",
                     "gitleaks is not on PATH, see README")
class ScanTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        with open(os.path.join(self.root, "README.md"), "w") as f:
            f.write("# demo\n")

    def test_clean_folder_passes(self):
        self.assertEqual(run(self.root)[0], 0)

    def test_fake_token_fails_and_is_redacted(self):
        token = write_token(self.root)
        code, out = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("github-pat", out)
        self.assertIn("config.py", out)
        self.assertNotIn(token, out)

    # The target repo must not be able to switch the check off.
    def test_repo_config_allowlisting_everything_is_ignored(self):
        write(self.root, ".gitleaks.toml", '[allowlist]\npaths = [".*"]\n')
        write_token(self.root)
        self.assertEqual(run(self.root)[0], 1)

    def test_gitleaks_allow_comment_is_ignored(self):
        write_token(self.root, "  # gitleaks:allow")
        self.assertEqual(run(self.root)[0], 1)

    # gitleaks always reads a .gitleaksignore at the scanned root, and no
    # flag turns that off, so the check fails on the file itself.
    def test_repo_gitleaksignore_fails(self):
        write(self.root, ".gitleaksignore", "\n")
        code, out = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn(".gitleaksignore: not allowed", out)

    # gitleaks reads a .gitleaksignore in the current folder by default.
    # The scan must not honor one there either.
    def test_gitleaksignore_in_current_folder_is_ignored(self):
        write_token(self.root)
        code, out = run(self.root)
        self.assertEqual(code, 1)
        fingerprint = re.search(r"Fingerprint: *(\S+)", out).group(1)
        with tempfile.TemporaryDirectory() as cwd:
            write(cwd, ".gitleaksignore", fingerprint + "\n")
            self.assertEqual(run(self.root, cwd=cwd)[0], 1)

    # The default gitleaks config skips the first four paths. The org
    # config skips none of them, and no common secrets file either.
    def test_no_path_is_skipped(self):
        for name in ["sub/gitleaks.toml", "node_modules/a.js", "package-lock.json", "logo.svg",
                     ".env", "config/secrets.yml"]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                write_token(root, name=name)
                self.assertEqual(run(root)[0], 1)

    # Its regex is edited in gitleaks.toml, so check it still matches.
    def test_bedrock_short_lived_rule_still_fires(self):
        # Built with join: Python folds "a" + "b" into one string in the .pyc,
        # and the scan of this repo would then find it.
        key = "".join(["bedrock-api-key-", "YmVkcm9jay5h", "bWF6b25hd3MuY29t"])
        write(self.root, "a.py", f'K = "{key}"\n')
        code, out = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("aws-amazon-bedrock-api-key-short-lived", out)

    def test_token_inside_zip_fails(self):
        token = fake_github_token()
        with zipfile.ZipFile(os.path.join(self.root, "a.zip"), "w") as z:
            z.writestr("config.py", f'TOKEN = "{token}"\n')
        code, out = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("a.zip!config.py", out)

    # Two levels deep, so a max_archive_depth of 1 fails this test.
    def test_token_in_zip_inside_zip_fails(self):
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as z:
            z.writestr("config.py", token_file_bytes())
        with zipfile.ZipFile(os.path.join(self.root, "outer.zip"), "w") as z:
            z.writestr("inner.zip", inner.getvalue())
        code, out = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("outer.zip!inner.zip!config.py", out)

    def test_token_inside_tar_gz_fails(self):
        data = token_file_bytes()
        with tarfile.open(os.path.join(self.root, "a.tar.gz"), "w:gz") as t:
            info = tarfile.TarInfo("config.py")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
        self.assertEqual(run(self.root)[0], 1)

    # Runs the workflow's own scan line in the runner layout: the target
    # repo in "target", this repo in ".org-check". Fails if the step stops
    # scanning "target" or ignores the scan's exit code.
    def test_workflow_step_fails_on_secret_in_target(self):
        write_token(os.path.join(self.root, "target"))
        shutil.copytree(REPO, os.path.join(self.root, ".org-check"),
                        ignore=shutil.ignore_patterns(".git"))
        p = subprocess.run(["bash", "-e", "-c", workflow_run_command("Secret scan")],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()

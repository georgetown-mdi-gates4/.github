"""Find repos in an org with no README or no .gitignore, and open one PR
per repo that adds the missing files.

Dry run by default: prints one plan line per repo and writes nothing.
With --apply it creates one branch and one PR per repo that has gaps,
through `gh api` (no local clone). Skips forks, archived repos, empty
repos, and repos with an open PR from the backfill branch.

A README counts when the repo root holds README or README.<anything>,
in any case. The .gitignore must be named exactly `.gitignore`.
A file is missing only when it is absent from a root listing that
succeeded. Any failed `gh` call prints an error line for that repo and
makes the exit code 1. Exit 2 is bad usage.

config.json holds the branch name, the PR title, the commit message, the file
names and the path to each template. templates/ holds the text of each file
and of the PR body.

Run: python3 backfill/backfill.py <org> [--apply]
"""
import argparse
import base64
import json
import os
import subprocess
import sys
from string import Template

HERE = os.path.dirname(os.path.abspath(__file__))


class GhError(Exception):
    pass


def gh(*args, body=None):
    p = subprocess.run(["gh", *args], capture_output=True, text=True,
                       input=None if body is None else json.dumps(body))
    if p.returncode != 0:
        raise GhError(f"gh {' '.join(args)}: {p.stderr.strip()}")
    return json.loads(p.stdout or "null")


def read(path):
    with open(os.path.join(HERE, path)) as f:
        return f.read()


def missing(names, config):
    stem = config["readme_stem"]
    lower = [n.lower() for n in names]
    has_readme = any(n == stem or n.startswith(stem + ".") for n in lower)
    return [path for path in config["files"]
            if path not in names and not (path.lower().split(".")[0] == stem and has_readme)]


def plan(org, r, config):
    """Return (status line, list of missing files) for one repo."""
    for flag, reason in (("isFork", "fork"), ("isArchived", "archived"), ("isEmpty", "empty")):
        if r[flag]:
            return f"skipped ({reason})", []
    name = f"repos/{org}/{r['name']}"
    prs = gh("api", f"{name}/pulls?state=open&head={org}:{config['branch']}")
    if prs:
        return f"skipped (open backfill PR #{prs[0]['number']})", []
    gaps = missing([e["name"] for e in gh("api", f"{name}/contents") if e["type"] != "dir"], config)
    return (f"missing {', '.join(gaps)}" if gaps else "ok"), gaps


def apply(org, r, gaps, config):
    name, base, branch = f"repos/{org}/{r['name']}", r["defaultBranchRef"]["name"], config["branch"]
    sha = gh("api", f"{name}/git/ref/heads/{base}")["object"]["sha"]
    gh("api", "-X", "POST", f"{name}/git/refs", "--input", "-",
       body={"ref": f"refs/heads/{branch}", "sha": sha})
    for path in gaps:
        text = Template(read(config["files"][path]["template"])).safe_substitute(repo=r["name"])
        gh("api", "-X", "PUT", f"{name}/contents/{path}", "--input", "-", body={
            "message": Template(config["commit_message"]).safe_substitute(path=path),
            "content": base64.b64encode(text.encode()).decode(),
            "branch": branch,
        })
    added = "\n".join(f"- `{p}`: {config['files'][p]['why']}" for p in gaps)
    pr_body = Template(read(config["pr_body"])).safe_substitute(added=added, org=org)
    pr = gh("api", "-X", "POST", f"{name}/pulls", "--input", "-", body={
        "title": config["pr_title"], "head": branch, "base": base, "body": pr_body})
    return pr["html_url"]


def main(argv):
    ap = argparse.ArgumentParser(description="Backfill README and .gitignore across an org.")
    ap.add_argument("org")
    ap.add_argument("--apply", action="store_true", help="open the PRs (default: print the plan only)")
    args = ap.parse_args(argv)
    config = json.loads(read("config.json"))
    try:
        repos = gh("repo", "list", args.org, "--limit", str(config["repo_limit"]),
                   "--json", "name,isFork,isArchived,isEmpty,defaultBranchRef")
    except GhError as err:
        print(f"{args.org}: error ({err})")
        return 1
    failed = False
    for r in repos:
        label = f"{args.org}/{r['name']}"
        try:
            line, gaps = plan(args.org, r, config)
            print(f"{label}: {line}")
            if args.apply and gaps:
                print(f"{label}: opened {apply(args.org, r, gaps, config)}")
        except GhError as err:
            print(f"{label}: error ({err})")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

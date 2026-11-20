"""Tests for scan.sh. Each test builds a folder in a temp dir, runs the
scan on it, and checks the exit code and the printed result.

The fake token is built at run time from pieces, so this repo never holds
a string that looks like a real secret (the check scans this repo too).

Run: python3 -m unittest discover -s secret-scan -v
"""
import os
import re
import secrets
import shutil
import string
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "scan.sh")
REPO = os.path.dirname(HERE)
WORKFLOW = os.path.join(REPO, ".github", "workflows", "data-check.yml")


def fake_github_token():
    body = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))
    return "_".join(["ghp", body])


def write_token(folder, suffix=""):
    token = fake_github_token()
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "config.py"), "w") as f:
        f.write(f'TOKEN = "{token}"{suffix}\n')
    return token


def write(folder, name, text):
    with open(os.path.join(folder, name), "w") as f:
        f.write(text)


def workflow_scan_command():
    with open(WORKFLOW) as f:
        m = re.search(r"- name: Secret scan\n(?:\s+if: .*\n)?\s+run: (.+)", f.read())
    assert m, "no 'Secret scan' step with a one-line run in the workflow"
    return m.group(1)


def run(path):
    p = subprocess.run(["sh", SCRIPT, path], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


@unittest.skipUnless(shutil.which("gitleaks"), "gitleaks is not on PATH, see README")
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

    # Runs the workflow's own scan line in the runner layout: the target
    # repo in "target", this repo in ".org-check". Fails if the step stops
    # scanning "target" or ignores the scan's exit code.
    def test_workflow_step_fails_on_secret_in_target(self):
        write_token(os.path.join(self.root, "target"))
        shutil.copytree(REPO, os.path.join(self.root, ".org-check"),
                        ignore=shutil.ignore_patterns(".git"))
        p = subprocess.run(["bash", "-eo", "pipefail", "-c", workflow_scan_command()],
                           cwd=self.root, capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()

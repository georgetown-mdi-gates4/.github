"""Tests for install.sh. No network: a fake curl on PATH copies a fake
tarball built here, and the tests compute its sha256 for the pin file.

Run: python3 -m unittest discover -s secret-scan -v
"""
import hashlib
import io
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest

from test_scan import REPO, workflow_run_command

FAKE_CURL = """#!/bin/sh
# Copies $FAKE_TARBALL to the -o path and logs the URL.
while [ $# -gt 0 ]; do
  case "$1" in
    -o) out=$2; shift ;;
    -*) ;;
    *) echo "$1" >> "$CURL_LOG" ;;
  esac
  shift
done
cp "$FAKE_TARBALL" "$out"
"""


class InstallTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        # The runner layout: this repo in ".org-check".
        self.org = os.path.join(self.root, ".org-check")
        shutil.copytree(REPO, self.org, ignore=shutil.ignore_patterns(".git"))
        bin_dir = os.path.join(self.root, "fakebin")
        os.mkdir(bin_dir)
        with open(os.path.join(bin_dir, "curl"), "w") as f:
            f.write(FAKE_CURL)
        os.chmod(os.path.join(bin_dir, "curl"), 0o755)
        self.tarball = os.path.join(self.root, "release.tar.gz")
        with tarfile.open(self.tarball, "w:gz") as t:
            data = b"#!/bin/sh\necho fake gitleaks\n"
            info = tarfile.TarInfo("gitleaks")
            info.size, info.mode = len(data), 0o755
            t.addfile(info, io.BytesIO(data))
        with open(self.tarball, "rb") as f:
            self.sha = hashlib.sha256(f.read()).hexdigest()
        self.github_path = os.path.join(self.root, "github_path")
        self.env = dict(os.environ, PATH=bin_dir + os.pathsep + os.environ["PATH"],
                        FAKE_TARBALL=self.tarball, CURL_LOG=os.path.join(self.root, "curl.log"),
                        RUNNER_TEMP=os.path.join(self.root, "runner_temp"),
                        GITHUB_PATH=self.github_path)
        self.dest = os.path.join(self.env["RUNNER_TEMP"], "gitleaks")

    def pin(self, sha):
        with open(os.path.join(self.org, "secret-scan", "gitleaks-release.env"), "w") as f:
            f.write(f"GITLEAKS_VERSION=8.30.1\nGITLEAKS_SHA256={sha}\n")

    # Runs the workflow's own install line, as GitHub runs it.
    def install(self):
        return subprocess.run(["bash", "-e", "-c", workflow_run_command("Install gitleaks")],
                              cwd=self.root, env=self.env, capture_output=True, text=True)

    def test_matching_sha_installs_and_adds_to_path(self):
        self.pin(self.sha)
        p = self.install()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(os.access(os.path.join(self.dest, "gitleaks"), os.X_OK))
        with open(self.github_path) as f:
            self.assertEqual(f.read(), self.dest + "\n")
        with open(self.env["CURL_LOG"]) as f:
            self.assertEqual(f.read(), "https://github.com/gitleaks/gitleaks/releases/download/"
                                       "v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz\n")

    def test_wrong_sha_fails_and_installs_nothing(self):
        self.pin("0" * 64)
        p = self.install()
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.dest, "gitleaks")))
        self.assertFalse(os.path.exists(self.github_path) and os.path.getsize(self.github_path))

    def test_pin_file_is_a_real_sha256(self):
        with open(os.path.join(REPO, "secret-scan", "gitleaks-release.env")) as f:
            pin = dict(l.strip().split("=", 1) for l in f if l.strip() and not l.startswith("#"))
        self.assertEqual(set(pin), {"GITLEAKS_VERSION", "GITLEAKS_SHA256"})
        self.assertRegex(pin["GITLEAKS_SHA256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()

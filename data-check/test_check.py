"""Tests for check.py. Each test builds a fake repo folder in a temp dir,
runs the script on it, and checks the printed lines and the exit code.

Run: python3 -m unittest discover -s data-check -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check.py")
with open(os.path.join(HERE, "rules.json")) as f:
    LIMIT = json.load(f)["max_bytes"]
BIG = 2 * LIMIT
SIZE_REASON = f"over {LIMIT} bytes"
TYPE_REASON = "data file type under a data or index folder"


def make(root, rel, size=10):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.truncate(size)  # sparse, so a 2 MB file costs no time


def run(path, script=SCRIPT):
    p = subprocess.run([sys.executable, script, path], capture_output=True, text=True)
    return p.stdout.splitlines(), p.returncode, p.stderr


def as_root():
    return os.geteuid() == 0


class CheckTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)  # cleanups run last-in first-out, so after any chmod restore
        self.root = tmp.name
        make(self.root, "README.md")

    def assertRun(self, lines, code):
        self.assertEqual(run(self.root)[:2], (lines, code))

    def lock(self, path, mode):
        os.chmod(path, mode)
        self.addCleanup(os.chmod, path, 0o755)

    def test_clean_repo(self):
        make(self.root, "src/app.py")
        self.assertRun([], 0)

    def test_big_file_at_root(self):
        make(self.root, "dump.bin", BIG)
        self.assertRun([f"dump.bin: {SIZE_REASON}"], 1)

    def test_docx_under_data(self):
        make(self.root, "data/report.docx")
        self.assertRun([f"data/report.docx: {TYPE_REASON}"], 1)

    def test_jsonl_under_index(self):
        make(self.root, "index/chunks.jsonl")
        self.assertRun([f"index/chunks.jsonl: {TYPE_REASON}"], 1)

    def test_upper_case_csv_under_nested_data(self):
        make(self.root, "nested/data/rows.CSV")
        self.assertRun([f"nested/data/rows.CSV: {TYPE_REASON}"], 1)

    def test_small_csv_in_fixtures_passes(self):
        make(self.root, "tests/fixtures/data/rows.csv")
        self.assertRun([], 0)

    def test_big_file_in_fixtures_fails(self):
        make(self.root, "tests/fixtures/big.csv", BIG)
        self.assertRun([f"tests/fixtures/big.csv: {SIZE_REASON}"], 1)

    def test_csv_outside_data_and_index_passes(self):
        make(self.root, "results/rows.csv")
        self.assertRun([], 0)

    def test_big_file_under_git_is_ignored(self):
        make(self.root, ".git/objects/pack/big.pack", BIG)
        self.assertRun([], 0)

    def test_both_reasons_and_sorted_output(self):
        make(self.root, "z.bin", BIG)
        make(self.root, "data/big.parquet", BIG)
        self.assertRun([
            f"data/big.parquet: {SIZE_REASON}; {TYPE_REASON}",
            f"z.bin: {SIZE_REASON}",
        ], 1)

    def test_missing_path(self):
        lines, code, err = run(os.path.join(self.root, "no-such-folder"))
        self.assertEqual((lines, code), ([], 2))
        self.assertIn("usage: check.py <repo folder>", err)

    def test_npy_under_data(self):
        make(self.root, "data/vec.npy")
        self.assertRun([f"data/vec.npy: {TYPE_REASON}"], 1)

    def test_pdf_under_index(self):
        make(self.root, "index/paper.pdf")
        self.assertRun([f"index/paper.pdf: {TYPE_REASON}"], 1)

    def test_folder_name_is_whole_word(self):
        make(self.root, "metadata/x.csv")
        make(self.root, "mydata/x.csv")
        self.assertRun([], 0)

    def test_fixtures_only_at_root(self):
        make(self.root, "src/tests/fixtures/data/x.csv")
        make(self.root, "tests/fixtures2/data/x.csv")
        self.assertRun([
            f"src/tests/fixtures/data/x.csv: {TYPE_REASON}",
            f"tests/fixtures2/data/x.csv: {TYPE_REASON}",
        ], 1)

    def test_limit_is_the_org_standard(self):
        # The org standard (CONTRIBUTING.md) promises 1 MB = 1,048,576 bytes.
        # A change to rules.json alone must not quietly change that promise.
        self.assertEqual(LIMIT, 1048576)

    def test_size_boundary(self):
        make(self.root, "at.bin", LIMIT)
        make(self.root, "over.bin", LIMIT + 1)
        self.assertRun([f"over.bin: {SIZE_REASON}"], 1)

    def test_folder_case_does_not_matter(self):
        make(self.root, "Data/survey.csv")
        make(self.root, "INDEX/vec.npy")
        self.assertRun([
            f"Data/survey.csv: {TYPE_REASON}",
            f"INDEX/vec.npy: {TYPE_REASON}",
        ], 1)

    def test_symlink_counts_at_own_size(self):
        with tempfile.TemporaryDirectory() as outside:
            make(outside, "big.bin", BIG)
            os.symlink(os.path.join(outside, "big.bin"), os.path.join(self.root, "link.bin"))
            self.assertRun([], 0)

    def test_dangling_symlink_under_data(self):
        os.makedirs(os.path.join(self.root, "data"))
        os.symlink(os.path.join(self.root, "gone"), os.path.join(self.root, "data", "x.txt"))
        self.assertRun([], 0)

    def test_nested_git_is_ignored(self):
        make(self.root, "vendor/lib/.git/big.pack", BIG)
        self.assertRun([], 0)

    @unittest.skipIf(as_root(), "root can read everything")
    def test_unlistable_folder_fails(self):
        make(self.root, "secret/data/x.csv")
        self.lock(os.path.join(self.root, "secret"), 0)
        self.assertRun(["secret: cannot read (Permission denied)"], 1)

    @unittest.skipIf(as_root(), "root can read everything")
    def test_unreadable_root_fails(self):
        make(self.root, "dump.bin", BIG)
        self.lock(self.root, 0)
        self.assertRun([".: cannot read (Permission denied)"], 1)

    @unittest.skipIf(as_root(), "root can read everything")
    def test_lstat_failure_fails(self):
        make(self.root, "locked/a.txt")
        self.lock(os.path.join(self.root, "locked"), 0o444)  # list, no stat
        self.assertRun(["locked/a.txt: cannot read (Permission denied)"], 1)

    def bad_rules(self, text):
        bin_dir = os.path.join(self.root, "bin")
        os.makedirs(bin_dir)
        script = shutil.copy(SCRIPT, bin_dir)
        if text is not None:
            with open(os.path.join(bin_dir, "rules.json"), "w") as f:
                f.write(text)
        make(self.root, "data/x.csv")
        return run(self.root, script)[1]

    def test_missing_rules_fails(self):
        self.assertNotEqual(self.bad_rules(None), 0)

    def test_invalid_rules_fails(self):
        self.assertNotEqual(self.bad_rules("{not json"), 0)


if __name__ == "__main__":
    unittest.main()

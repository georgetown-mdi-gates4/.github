"""Tests for check.py. Each test builds a fake repo folder in a temp dir,
runs the script on it, and checks the printed lines and the exit code.

Run: python3 -m unittest discover -s data-check -v
"""
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check.py")
BIG = 2 * 1024 * 1024
SIZE_REASON = "over 1048576 bytes"
TYPE_REASON = "data file type under a data or index folder"


def make(root, rel, size=10):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.truncate(size)  # sparse, so a 2 MB file costs no time


def run(path):
    p = subprocess.run([sys.executable, SCRIPT, path], capture_output=True, text=True)
    return p.stdout.splitlines(), p.returncode


class CheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        make(self.root, "README.md")

    def tearDown(self):
        self.tmp.cleanup()

    def assertRun(self, lines, code):
        self.assertEqual(run(self.root), (lines, code))

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
        lines, code = run(os.path.join(self.root, "no-such-folder"))
        self.assertEqual((lines, code), ([], 2))


if __name__ == "__main__":
    unittest.main()

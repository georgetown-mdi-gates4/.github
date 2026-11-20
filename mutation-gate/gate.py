"""Run the mutation gate on this repo's checks.

mutation_gate.py beside this file is the runner, vendored unchanged. It
expects `python3 <script> --demo` as each script's self-check. The checks
here are unittest suites in several folders, and the files they cover are
shell, TOML, YAML and Markdown too. So this file swaps the runner's
run_demo() for one that copies the whole repo, applies one mutation, and
runs every test suite (each folder with a test_*.py). The entry rules, the
parallel runs, the report and the exit codes stay the runner's own.

Run from the repo root, with gitleaks 8.30.1 on PATH:

    python3 mutation-gate/gate.py
"""
import functools
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import warnings

import mutation_gate as runner

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# REQUIRE_GITLEAKS=1: without gitleaks the scan tests fail, not skip, so
# the baseline fails loudly instead of letting every scan mutant survive.
ENV = dict(os.environ, REQUIRE_GITLEAKS="1", PYTHONDONTWRITEBYTECODE="1")


def run_tests(scripts_dir, script, mutation=None):
    """True when every suite passes on a copy of the repo with `mutation` applied."""
    return baseline() if mutation is None else _run(scripts_dir, script, mutation)


@functools.cache
def baseline():
    """The unmutated run, once: the runner asks for it per mutated file."""
    return _run(None, None, None)


def _run(scripts_dir, script, mutation):
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "repo")
        shutil.copytree(REPO, work, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        if mutation:
            path = os.path.join(work, os.path.relpath(scripts_dir, REPO), script)
            with open(path) as f:
                source = f.read()
            with open(path, "w") as f:
                f.write(source.replace(mutation["find"], mutation["replace"], 1))
        suites = sorted({os.path.dirname(p) for p in glob.glob(os.path.join(work, "*", "test_*.py"))})
        try:
            return all(subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", s],
                                      cwd=work, env=ENV, capture_output=True,
                                      timeout=runner.DEMO_TIMEOUT_SECONDS).returncode == 0
                       for s in suites)
        except subprocess.TimeoutExpired:
            return False  # the runner's rule: a hang counts as killed


def main(argv):
    if "--demo" not in argv:  # --demo is the runner's self-check on its own fixtures
        runner.run_demo = run_tests
    if all(a.startswith("--") for a in argv):
        argv = argv + [os.path.join(HERE, "mutations.json")]
    # The runner ast-parses each mutated file to find a _demo. gitleaks.toml
    # parses as Python with invalid-escape warnings that mean nothing here.
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    runner.main(argv)


if __name__ == "__main__":
    main(sys.argv[1:])

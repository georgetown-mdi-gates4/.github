"""Run the mutation gate on this repo's checks.

mutation_gate.py beside this file is the runner, vendored unchanged. It
expects `python3 <script> --demo` as each script's self-check. The checks
here are unittest suites in several folders, and the files they cover are
shell, TOML, YAML and Markdown too. So this file swaps the runner's
run_demo() for one that copies the whole repo, applies one mutation, and
runs every test suite (each folder with a test_*.py). The entry rules, the
report and the exit codes stay the runner's own.

A mutant counts as killed only when a test FAILS. A mutant that times out,
does not compile, or makes a test ERROR proves nothing, so the gate names
it and exits 1.

Run from the repo root, with gitleaks on PATH at the GITLEAKS_VERSION in
secret-scan/gitleaks-release.env:

    python3 mutation-gate/gate.py              # the gate
    python3 mutation-gate/gate.py --self-test  # this file's own logic, on fixtures
"""
import contextlib
import functools
import glob
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import warnings

import mutation_gate as runner

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
# REQUIRE_GITLEAKS=1 makes the scan tests fail when gitleaks is missing, so
# the baseline fails loudly instead of letting every scan mutant survive.
ENV = dict(os.environ, REQUIRE_GITLEAKS="1", PYTHONDONTWRITEBYTECODE="1")
# The runner starts one thread per core. Each mutant runs three suites that
# start their own processes (gitleaks is multi-threaded), so a full pool
# slowed one suite from 6.6 s to 25 s. Half the cores keeps each suite far
# below the runner's 60 s limit: on a 4-core ubuntu-latest runner, 2 at a time.
SLOTS = threading.BoundedSemaphore(max(1, (os.cpu_count() or 2) // 2))
# Runs one suite and writes its failure and error counts to argv[2].
SUITE = ("import json, sys, unittest\n"
         "r = unittest.TextTestRunner(stream=sys.stderr).run(unittest.defaultTestLoader.discover(sys.argv[1]))\n"
         "json.dump([len(r.failures), len(r.errors)], open(sys.argv[2], 'w'))\n")
PROBLEMS = []  # every timeout and broken mutant, by name
SURVIVED = []  # kept here too: the runner never reports them once a run is broken


class Broken(Exception):
    """A run that proves nothing: it timed out, or the mutant did not even load."""


def run_tests(scripts_dir, script, mutation=None):
    """True when every suite passes on a copy of the repo with `mutation` applied."""
    if mutation is None:
        return baseline()
    alive = _run(scripts_dir, script, mutation)
    SURVIVED.extend([f"SURVIVED {script}: {mutation['label']}"] if alive else [])
    return alive


@functools.cache
def baseline():
    """The unmutated run, once: the runner asks for it per mutated file."""
    try:
        return _run(None, None, None)
    except Broken as e:
        print(e, file=sys.stderr)
        return False  # the runner then prints "--demo fails BEFORE any mutation"


def _broken(name, why):
    PROBLEMS.append(f"BROKEN {name}: {why}")
    raise Broken(PROBLEMS[-1])


def _run(scripts_dir, script, mutation):
    name = f"{script}: {mutation['label']}" if mutation else "the unmutated repo"
    with SLOTS, tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "repo")
        shutil.copytree(REPO, work, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        if mutation:
            path = os.path.join(work, os.path.relpath(scripts_dir, REPO), script)
            with open(path) as f:
                source = f.read().replace(mutation["find"], mutation["replace"], 1)
            with open(path, "w") as f:
                f.write(source)
            if path.endswith(".py"):
                try:
                    compile(source, path, "exec")
                except SyntaxError as e:
                    _broken(name, f"the mutated file does not compile ({e.msg}, line {e.lineno})")
        for suite in sorted({os.path.dirname(p) for p in glob.glob(os.path.join(work, "*", "test_*.py"))}):
            failures, errors = _suite(work, suite, os.path.join(tmp, "counts.json"), name)
            if errors:
                _broken(name, f"{errors} test(s) in {os.path.basename(suite)} error instead of fail")
            if failures:
                return False
        return True


def _suite(work, suite, counts, name):
    """(failures, errors) of one suite. On timeout, kill its whole process group."""
    p = subprocess.Popen([sys.executable, "-c", SUITE, suite, counts], cwd=work, env=ENV,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        p.wait(timeout=runner.DEMO_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.wait()
        _broken(name, f"TIMED OUT after {runner.DEMO_TIMEOUT_SECONDS} s in {os.path.basename(suite)}")
    try:
        with open(counts) as f:
            return tuple(json.load(f))
    except (OSError, ValueError):
        _broken(name, f"{os.path.basename(suite)} exited {p.returncode} without a test result")
    finally:
        with contextlib.suppress(OSError):
            os.remove(counts)


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if "--demo" not in argv:  # --demo is the runner's self-check on its own fixtures
        runner.run_demo = run_tests
    if all(a.startswith("--") for a in argv):
        argv = argv + [os.path.join(HERE, "mutations.json")]
    # The runner ast-parses each mutated file to find a _demo. gitleaks.toml
    # parses as Python with invalid-escape warnings that mean nothing here.
    warnings.filterwarnings("ignore", category=SyntaxWarning)
    try:
        runner.main(argv)
    except Broken:  # raised in a pool thread; the pool has finished every mutant by now
        raise SystemExit(f"{len(PROBLEMS)} mutation run(s) proved nothing:\n" + "\n".join(PROBLEMS + SURVIVED))


def self_test():
    """This file's own logic, on a fixture repo. A flag, not a test_*.py, because
    the gate runs every test_*.py inside every mutant run."""
    global REPO
    real = REPO, runner.DEMO_TIMEOUT_SECONDS
    test = ("import os, unittest\nimport target\n\n\nclass T(unittest.TestCase):\n"
            "    def test_x(self):\n        self.assertEqual(os.environ.get('REQUIRE_GITLEAKS'), '1')\n"
            "        self.assertEqual(target.X, 1)\n")

    def gate(target, replace, timeout=10):
        """(exit code, all output) of the gate on a fixture whose one mutation is `replace`."""
        with tempfile.TemporaryDirectory() as tmp:
            global REPO
            REPO, runner.DEMO_TIMEOUT_SECONDS = tmp, timeout
            os.makedirs(os.path.join(tmp, "pkg"))
            os.makedirs(os.path.join(tmp, "gate"))
            for rel, text in (("pkg/target.py", target), ("pkg/test_t.py", test)):
                with open(os.path.join(tmp, rel), "w") as f:
                    f.write(text)
            entry = {"script": "../pkg/target.py", "label": "fixture", "find": "X = 1", "replace": replace, "source": "#0"}
            with open(os.path.join(tmp, "gate", "mutations.json"), "w") as f:
                json.dump({"mutations": [entry]}, f)
            baseline.cache_clear()
            PROBLEMS.clear()
            SURVIVED.clear()
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                    main([os.path.join(tmp, "gate", "mutations.json")])
                return 0, out.getvalue()
            except SystemExit as e:
                return (e.code if isinstance(e.code, int) else 1), out.getvalue() + str(e.code)

    assert ENV.get("REQUIRE_GITLEAKS") == "1", "REQUIRE_GITLEAKS=1 is missing from the test runs' environment"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = os.path.join(tmp, "pid")
            grandchild = f"import os, time; open({pid_file!r}, 'w').write(str(os.getpid())); time.sleep(60)"
            hang = f"import subprocess, sys\nsubprocess.run([sys.executable, '-c', {grandchild!r}])\nX = 1"
            code, out = gate("X = 1\n", hang, timeout=3)
            assert code == 1 and "TIMED OUT" in out, f"a timeout is reported and fails the gate: {out}"
            pid = int(open(pid_file).read())
            for _ in range(50):  # the killed grandchild needs a moment to be reaped
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.1)
            else:
                raise AssertionError("a timeout kills the whole process group, grandchildren too")
        code, out = gate("X = 1\n", "X = 2")
        assert code == 0 and "1 mutations, 0 survived" in out, f"a mutant a test fails on is killed: {out}"
        code, out = gate("X = 1\nX = 2\n", "X = 3")
        assert code == 1 and "BEFORE any mutation" in out, f"a failing baseline fails the gate: {out}"
        code, out = gate("X = 1\n", "X = 1 / 0")
        assert code == 1 and "error instead of fail" in out, f"a mutant whose tests error fails the gate: {out}"
        code, out = gate("X = 1\n", "X = (")
        assert code == 1 and "does not compile" in out, f"a mutant that does not compile fails the gate: {out}"
        code, out = gate("X = 1\n", "X = 1  # same")
        assert code == 1 and "SURVIVED" in out, f"a surviving mutant fails the gate: {out}"
    finally:
        REPO, runner.DEMO_TIMEOUT_SECONDS = real
    print("self-test ok")


if __name__ == "__main__":
    main(sys.argv[1:])

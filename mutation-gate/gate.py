"""Run the mutation gate on this repo's checks.

mutation_gate.py beside this file is the runner, vendored unchanged. It
expects `python3 <script> --demo` as each script's self-check. The checks
here are unittest suites in several folders, and the files they cover are
shell, TOML, YAML and Markdown too. So this file swaps the runner's
run_demo() for one that copies the whole repo, applies one mutation, and
runs every test suite (each folder with a test_*.py). The entry rules, the
report and the exit codes stay the runner's own.

A mutant counts as killed only when a test FAILS. A mutant that times out,
does not compile, makes a test ERROR, or ends a suite without a test result
proves nothing, so the gate names it and exits 1.

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
# below runner.DEMO_TIMEOUT_SECONDS. On a 4-core ubuntu-latest runner,
# that is 2 at a time.
SLOTS = threading.BoundedSemaphore(max(1, (os.cpu_count() or 2) // 2))
# Runs one suite and prints its counts last on stdout, as "GATE-COUNTS <failures> <errors>".
# The gate reads the last such line of that suite's own stdout, so no file is shared.
MARK = "GATE-COUNTS"
SUITE = ("import sys, unittest\n"
         "r = unittest.TextTestRunner(stream=sys.stderr)"
         ".run(unittest.defaultTestLoader.discover(sys.argv[1]))\n"
         f"print('\\n{MARK}', len(r.failures), len(r.errors))\n")
PROBLEMS = []  # every timeout and broken mutant, by name
SURVIVED = []  # kept here too: the runner never reports them once a run is broken


class Broken(Exception):
    """A run that proves nothing: a timeout, a file that does not compile,
    a test error, or a suite that ends without a test result."""


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
        tests = glob.glob(os.path.join(work, "*", "test_*.py"))
        for suite in sorted({os.path.dirname(p) for p in tests}):
            failures, errors = _suite(work, suite, name)
            if errors:
                _broken(name, f"{errors} test(s) in {os.path.basename(suite)} "
                              "error instead of fail")
            if failures:
                return False
        return True


def _suite(work, suite, name):
    """(failures, errors) of one suite, from the last MARK line of its stdout.
    On timeout, kill its whole process group."""
    p = subprocess.Popen([sys.executable, "-c", SUITE, suite], cwd=work, env=ENV, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        out = p.communicate(timeout=runner.DEMO_TIMEOUT_SECONDS)[0]
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        _broken(name, f"TIMED OUT after {runner.DEMO_TIMEOUT_SECONDS} s "
                      f"in {os.path.basename(suite)}")
    counts = [line.split()[1:] for line in out.splitlines() if line.startswith(MARK + " ")]
    if not counts:
        _broken(name, f"{os.path.basename(suite)} exited {p.returncode} without a test result")
    return tuple(int(n) for n in counts[-1])


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
    # Raised in a pool thread. The pool cancels the mutants not yet started
    # and waits for the running ones, so PROBLEMS and SURVIVED are final here.
    except Broken:
        raise SystemExit(f"{len(PROBLEMS)} mutation run(s) proved nothing:\n"
                         + "\n".join(PROBLEMS + SURVIVED))


def self_test():
    """This file's own logic, on a fixture repo. A flag, not a test_*.py, because
    the gate runs every test_*.py inside every mutant run. Its checks raise
    AssertionError themselves, so `python3 -O` keeps them."""
    global REPO
    real = REPO, runner.DEMO_TIMEOUT_SECONDS
    # The fake count line first: the gate must read the suite's last count line.
    test = (f"import os, unittest\nimport target\nprint('{MARK} 0 0')\n\n\n"
            "class T(unittest.TestCase):\n    def test_x(self):\n"
            "        self.assertEqual(os.environ.get('REQUIRE_GITLEAKS'), '1')\n"
            "        self.assertEqual(target.X, 1)\n")

    def gate(target, *replaces, timeout=10, extra=()):
        """(exit code, all output) of the gate on a fixture with one mutation per `replaces`,
        labelled "fixture 0", "fixture 1" and so on. `extra` is more (path, text) files."""
        with tempfile.TemporaryDirectory() as tmp:
            global REPO
            REPO, runner.DEMO_TIMEOUT_SECONDS = tmp, timeout
            os.makedirs(os.path.join(tmp, "gate"))
            for rel, text in (("pkg/target.py", target), ("pkg/test_t.py", test), *extra):
                os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
                with open(os.path.join(tmp, rel), "w") as f:
                    f.write(text)
            entries = [{"script": "../pkg/target.py", "label": f"fixture {i}", "find": "X = 1",
                        "replace": r, "source": "#0"} for i, r in enumerate(replaces)]
            with open(os.path.join(tmp, "gate", "mutations.json"), "w") as f:
                json.dump({"mutations": entries}, f)
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

    def expect(ok, what, out=""):
        if not ok:
            raise AssertionError(f"{what}: {out}")

    expect(ENV.get("REQUIRE_GITLEAKS") == "1",
           "REQUIRE_GITLEAKS=1 is in the test runs' environment")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            pid_file = os.path.join(tmp, "pid")
            grandchild = (f"import os, time; open({pid_file!r}, 'w').write(str(os.getpid())); "
                          "time.sleep(60)")
            hang = (f"import subprocess, sys\n"
                    f"subprocess.run([sys.executable, '-c', {grandchild!r}])\nX = 1")
            code, out = gate("X = 1\n", hang, timeout=3)
            expect(code == 1 and "TIMED OUT" in out,
                   "a timeout is reported and fails the gate", out)
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
        expect(code == 0 and "1 mutations, 0 survived" in out,
               "a mutant a test fails on is killed", out)
        code, out = gate("X = 1\nX = 2\n", "X = 3")
        expect(code == 1 and "BEFORE any mutation" in out, "a failing baseline fails the gate", out)
        # The erroring suite sorts after the killing one, so only the baseline reaches it.
        erroring = ("zz/test_e.py", "import unittest\n\n\nclass E(unittest.TestCase):\n"
                    "    def test_e(self):\n        raise RuntimeError\n")
        code, out = gate("X = 1\n", "X = 2", extra=[erroring])
        expect(code == 1 and "BEFORE any mutation" in out,
               "a baseline whose tests error fails the gate", out)
        code, out = gate("X = 1\n", "X = 1 / 0")
        expect(code == 1 and "error instead of fail" in out,
               "a mutant whose tests error fails the gate", out)
        code, out = gate("X = 1\n", "X = (")
        expect(code == 1 and "does not compile" in out,
               "a mutant that does not compile fails the gate", out)
        # The middle suite (pkg) ends with no result. aa before it passes, zz after it fails.
        passing = ("aa/test_a.py", "import unittest\n\n\nclass A(unittest.TestCase):\n"
                   "    def test_a(self):\n        pass\n")
        failing = ("zz/test_z.py", "import unittest\n\n\nclass Z(unittest.TestCase):\n"
                   "    def test_z(self):\n"
                   "        self.assertNotIn('_exit', open('pkg/target.py').read())\n")
        code, out = gate("X = 1\n", "import os; os._exit(0)", extra=[passing, failing])
        expect(code == 1
               and "BROKEN ../pkg/target.py: fixture 0: pkg exited 0 without a test result" in out,
               "a suite with no test result fails the gate, even when a later suite fails", out)
        code, out = gate("X = 1\n", "X = 1  # same")
        expect(code == 1 and "SURVIVED" in out, "a surviving mutant fails the gate", out)
        # Fixture 1 is broken, so the runner never lists fixture 0. The gate must.
        code, out = gate("X = 1\n", "X = 1  # same", "X = (")
        expect(code == 1 and "SURVIVED ../pkg/target.py: fixture 0" in out
               and "BROKEN ../pkg/target.py: fixture 1" in out,
               "a broken run still lists the survivors", out)
    finally:
        REPO, runner.DEMO_TIMEOUT_SECONDS = real
    print("self-test ok")


if __name__ == "__main__":
    main(sys.argv[1:])

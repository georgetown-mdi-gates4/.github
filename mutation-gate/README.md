# mutation-gate

Proves each check's tests can fail. It applies each recorded mutation
(a small breakage of a check) to a copy of this repo and runs every test
suite. Each mutation must make a test fail. The workflow
`.github/workflows/mutation-gate.yml` runs it on every pull request in
this repo.

## Run

From the root of this repo, with gitleaks on PATH at the version that
`GITLEAKS_VERSION` in `secret-scan/gitleaks-release.env` names:

    python3 mutation-gate/gate.py              # every active mutation
    python3 mutation-gate/gate.py --list       # labels and sources
    python3 mutation-gate/gate.py --self-test  # gate.py's own logic, on fixtures
    python3 mutation-gate/mutation_gate.py --demo  # the runner's own logic

- Exit 0: every mutation fails at least one test.
- Exit 1: a mutation passes every test (`SURVIVED <file>: <label>`), an
  entry is unusable, or the tests fail before any mutation. That last
  case prints `--demo fails BEFORE any mutation`, e.g. when gitleaks is
  not on PATH. The scan tests always run with `REQUIRE_GITLEAKS=1`.
- Exit 1 also when a mutation run proves nothing (`BROKEN <file>:
  <label>: <cause>`). A mutation counts as caught only when a test fails.
  A run that times out, a mutated `.py` file that does not compile, a
  test that errors, and a suite that ends without a test result are each
  reported this way.

Half the cores run mutations at once, so each test run stays well inside
the runner's time limit (`DEMO_TIMEOUT_SECONDS` in `mutation_gate.py`). A
full run takes a few minutes.

## Add a mutation

An entry in `mutation-gate/mutations.json` needs a ticket that names the
rule or a review that found the breakage. `source` cites that ticket or
review.

    {"script": "../data-check/check.py",
     "label": "a file exactly at the size limit is rejected",
     "find": "if size > rules[\"max_bytes\"]:",
     "replace": "if size >= rules[\"max_bytes\"]:",
     "source": "#2 (ticket: break the size limit and a test fails), built in PR #9"}

- `script` is the file to mutate, relative to this folder.
- `find` must occur exactly once in that file. The gate replaces it
  with `replace`.
- Run the gate. A new entry that survives needs a test that catches it,
  in the same PR.
- To stop running an entry, move it to `retired` and add
  `"retired": "<date>"`. Do not delete it.

## Files

- `gate.py`: runs the gate. It reuses the runner and swaps only the step
  that runs the tests: it copies the repo, mutates one file, and runs the
  unittest suite of each folder with a `test_*.py`. Its own check is the
  `--self-test` flag. A `test_*.py` here would run inside every mutation
  run.
- `mutation_gate.py`: the runner, vendored unchanged from the yw-workflow
  plugin (`skills/mutation-gate/mutation_gate.py`, version 1.19.15),
  plus a two-line header. To check it against the plugin copy:

      diff <(sed '2,3d' mutation-gate/mutation_gate.py) <plugin folder>/skills/mutation-gate/mutation_gate.py

- `mutations.json`: the recorded mutations.

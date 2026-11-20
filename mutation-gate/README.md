# mutation-gate

Proves each check's tests can fail. It applies each recorded mutation
(a small breakage of a check) to a copy of this repo and runs every test
suite. Each mutation must make a test fail. The workflow
`.github/workflows/mutation-gate.yml` runs it on every pull request in
this repo.

## Run

From the root of this repo, with gitleaks 8.30.1 on PATH:

    python3 mutation-gate/gate.py          # every active mutation
    python3 mutation-gate/gate.py --list   # labels and sources

- Exit 0: every mutation fails at least one test.
- Exit 1: a mutation passes every test (`SURVIVED <file>: <label>`), an
  entry is unusable, or the tests fail before any mutation. That last
  case prints `--demo fails BEFORE any mutation`, e.g. when gitleaks is
  not on PATH. The scan tests always run with `REQUIRE_GITLEAKS=1`.

A full run takes about a minute.

## Add a mutation

Add an entry to `mutation-gate/mutations.json` only when a ticket names
the rule as one that must be provable by mutation, or a review found a
change that every test let through. `source` cites that ticket or PR.

    {"script": "../data-check/check.py",
     "label": "a file exactly at the size limit is rejected",
     "find": "if size > rules[\"max_bytes\"]:",
     "replace": "if size >= rules[\"max_bytes\"]:",
     "source": "#16"}

- `script` is the file to mutate, relative to this folder.
- `find` must occur exactly once in that file. The gate replaces it
  with `replace`.
- Run the gate. A new entry that survives needs a test that catches it,
  in the same PR.
- To stop running an entry, move it to `retired` and add
  `"retired": "<date>"`. Do not delete it.

## Files

- `gate.py`: runs the gate. It reuses the runner and swaps only the step
  that runs the tests: it copies the repo, mutates one file, and runs
  `python3 -m unittest discover -s <folder>` for each folder with a
  `test_*.py`.
- `mutation_gate.py`: the runner, vendored unchanged from the yw-workflow
  plugin (`skills/mutation-gate/mutation_gate.py`, version 1.19.15),
  plus a two-line header. To check it against the plugin copy:

      diff <(sed '2,3d' mutation-gate/mutation_gate.py) <plugin folder>/skills/mutation-gate/mutation_gate.py

- `mutations.json`: the recorded mutations.

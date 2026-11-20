# data-check

Rejects data files and large files in a repo folder. The workflow
`.github/workflows/data-check.yml` runs it on every pull request, before
the secret scan.

## Run

From the root of this repo:

    python3 data-check/check.py /path/to/repo

Exit 0 clean, 1 something rejected, 2 bad usage. It prints one line per
rejected file, `<path>: <reason>`, sorted.

## What it rejects

The rules live in `data-check/rules.json`. Read the values there.

- Any file over `max_bytes`.
- A file with a type in `data_extensions` under a folder named in
  `data_folders`, at any depth. Case does not matter for the type or the
  folder name, e.g. `Data/x.CSV` is rejected.
- A file or folder it cannot read.

## What it lets through

- A data file type outside a `data_folders` folder, e.g. `results.csv`
  at the repo root.
- A data file type under `tests/fixtures/` at the repo root (exact
  case). The size rule still applies there. A `tests/fixtures/` folder
  deeper in the tree gets no exception.
- Everything under a folder named in `skip_folders`. It does not walk
  those folders.

It reads file names and sizes only. It does not read file contents or
git history.

## Fix a finding

Delete the file from the branch, or move a small test file to
`tests/fixtures/`. List data paths in `.gitignore` to keep them out. A
file deleted in a later commit passes the check, but it stays in git
history.

## Tests

    python3 -m unittest discover -s data-check -v

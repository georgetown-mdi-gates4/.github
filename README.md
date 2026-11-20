# .github
Organization defaults: contributing standard, PR template, central check, backfill script

## Data file check

`data-check/check.py` rejects any file over the size limit, and data
files under any data or index folder. The size limit, the file types and
the folder names live in `data-check/rules.json`, so read them there.
Case does not matter for the data and index folder names or the file
types, e.g. `Data/x.CSV` is rejected. Files under `tests/fixtures/` at the
repo root (exact case) are exempt from the type rule only. The size rule
still applies. A `tests/fixtures/` folder deeper in the tree gets no
exception. A folder or
file the check cannot read fails the check.

Run it on a repo folder (exit 0 clean, 1 rejected, 2 bad usage):

    python3 data-check/check.py /path/to/your/repo

Run its tests:

    python3 -m unittest discover -s data-check -v

The workflow `.github/workflows/data-check.yml` runs the same check on
every pull request when the org ruleset requires it.

## Backfill: missing README and .gitignore

`backfill/backfill.py` lists the repos in an org and finds the ones whose
default branch has no README or no `.gitignore` at the root. A README
counts in any case and with any extension, e.g. `readme.MD` or `README`.
It skips forks, archived repos, empty repos, and repos that already have
an open PR from the backfill branch. It needs the `gh` CLI, logged in.

The org owner runs it by hand. First the dry run. It prints one line per
repo and changes nothing:

    python3 backfill/backfill.py georgetown-mdi-gates4

Then, after reading the plan, the apply run. It opens one branch and one
PR per repo with gaps. The PR adds only the missing files:

    python3 backfill/backfill.py georgetown-mdi-gates4 --apply

A failed `gh` call prints an `error` line for that repo, and the script
exits 1 at the end. It never counts a failed call as "file present".
The branch name, PR title and file list live in `backfill/config.json`.
The file contents and the PR body live in `backfill/templates/`.

Run its tests:

    python3 -m unittest discover -s backfill -v

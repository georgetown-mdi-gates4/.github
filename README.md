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

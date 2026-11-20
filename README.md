# .github
Organization defaults: contributing standard, PR template, central check, backfill script

## Data file check

`data-check/check.py` rejects any file over 1 MB, and data files
(`.npy .docx .pdf .jsonl .parquet .csv`) under any `data/` or `index/`
folder. Files under `tests/fixtures/` pass the type rule if they are under
1 MB. The rules live in `data-check/rules.json`.

Run it on a repo folder (exit 0 clean, 1 rejected, 2 bad usage):

    python3 data-check/check.py /path/to/your/repo

Run its tests:

    python3 -m unittest discover -s data-check -v

The workflow `.github/workflows/data-check.yml` runs the same check on
every pull request when the org ruleset requires it.

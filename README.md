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

## Secret scan

`secret-scan/scan.sh` runs [gitleaks](https://github.com/gitleaks/gitleaks)
(MIT license) on every file in a repo folder, with the config in
`secret-scan/gitleaks.toml` (the built-in rules). It
reads the files on disk, not git history, and skips the `.git` folder. It
prints the rule id, file and line of each finding, with the secret value
redacted. The workflow runs it on the target repo after the data check,
even when the data check fails. The gitleaks version and the sha256 of its
download are pinned in the workflow, and a download that does not match
stops the check.

A repo cannot opt out of the scan. Its own `.gitleaks.toml` and its
`gitleaks:allow` comments are ignored. A `.gitleaksignore` at the repo root
fails the scan, because gitleaks always reads that file. To fix a false
positive, change `secret-scan/gitleaks.toml` in this repo. Only the org
owners can make that change.

Run it locally with gitleaks 8.30.1 on your PATH (exit 0 clean, 1 finding,
2 bad usage):

    sh secret-scan/scan.sh /path/to/your/repo

Run its tests (they skip when gitleaks is not on PATH):

    python3 -m unittest discover -s secret-scan -v

On a finding, rotate the secret first: revoke the key at its provider and
make a new one. Then remove it from the files and keep the new key out of
git, e.g. in an environment variable or a `.env` file listed in
`.gitignore`. Removing the file alone is not enough, because the old key
stays in git history and in every clone.

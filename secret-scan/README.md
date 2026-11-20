# secret-scan

Scans every file in a repo folder for secrets with
[gitleaks](https://github.com/gitleaks/gitleaks) 8.30.1 (MIT license).
The workflow `.github/workflows/data-check.yml` runs it on the target
repo after the data check, also when the data check fails.

## Run

From the root of this repo, with gitleaks 8.30.1 on PATH:

    sh secret-scan/scan.sh /path/to/repo

- Exit 0: no finding.
- Exit 1: a finding, or a `.gitleaksignore` at the repo root.
- Exit 2: bad usage.
- A gitleaks error (e.g. a bad config) exits 1 or 2, so it fails too.

Each finding prints the rule id, file, line and fingerprint. The secret
value is redacted.

## Get gitleaks 8.30.1

`sh secret-scan/install.sh <folder>` downloads the linux_x64 build,
stops unless its sha256 matches `secret-scan/gitleaks-release.env`, puts
`gitleaks` in `<folder>` and prints the folder. Add that folder to PATH.
The workflow uses this script.

On another OS, download and extract
`https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_<os>_<arch>.tar.gz`,
e.g. `<os>_<arch>` = `darwin_arm64`.

## What it reads

- Every file on disk in the folder, with the rules in
  `secret-scan/gitleaks.toml` (the gitleaks default rules). It skips only
  the `.git` folder.
- The files inside `.zip` and `.tar.gz` files, also nested, up to
  `max_archive_depth` levels (set in `scan.sh`).

## What it does not read

- Git history.
- Binary files, e.g. `.pdf` and `.exe`.
- `.tgz` and `.docx` files. gitleaks treats them as binary and skips
  them with no message.

## A repo cannot opt out

- Its own `.gitleaks.toml` is ignored.
- Its `gitleaks:allow` comments are ignored.
- A `.gitleaksignore` at its root fails the scan, because gitleaks always
  reads that file. A `.gitleaksignore` in the current folder is ignored.

## Fix a finding

1. Rotate the secret first: revoke the key at its provider and make a
   new one. The old key stays in git history and in every clone, so
   removing the file alone leaves it exposed.
2. Remove the secret from the files.
3. Keep the new key out of git, e.g. in an environment variable or a
   `.env` file listed in `.gitignore`.

A false positive is fixed in this repo, by the org owners only: add an
allowlist to `secret-scan/gitleaks.toml`. Then set
`GITLEAKS_CONFIG_SHA256` in `secret-scan/gitleaks-release.env` to the
output of `sha256sum secret-scan/gitleaks.toml`, or the tests fail.

## Upgrade gitleaks

Change `GITLEAKS_VERSION` and `GITLEAKS_SHA256` in
`secret-scan/gitleaks-release.env`. Follow the upgrade steps in the
`secret-scan/gitleaks.toml` header. Change the version in this README.
A test fails when the three versions differ.

## Tests

From the root of this repo:

    PATH=/path/to/gitleaks-folder:$PATH REQUIRE_GITLEAKS=1 python3 -m unittest discover -s secret-scan -v

Without `REQUIRE_GITLEAKS=1`, the scan tests skip when gitleaks is not on
PATH. The install tests use a fake curl and need no network.

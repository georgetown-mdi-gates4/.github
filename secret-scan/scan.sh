#!/bin/sh
# Scan every file in a folder for secrets with gitleaks (dir mode, so the
# files on disk, not git history). Reads inside .zip and .tar.gz files,
# also nested, up to max_archive_depth levels deep. A .tgz or .docx file
# is treated as binary and skipped with no message. Binary files are not
# read. Prints rule
# id, file and line for each finding. Secret values are redacted. Uses
# gitleaks.toml beside this script. The scanned repo cannot opt out: its
# own .gitleaks.toml and gitleaks:allow comments are ignored. gitleaks
# always reads a .gitleaksignore at the scanned root, so that file fails
# the scan.
# Exit 0 clean, 1 finding, 2 bad usage. A gitleaks error (e.g. a bad
# config) also exits non-zero, 1 or 2, so it fails the check too.
#
# Run: sh secret-scan/scan.sh <repo folder>
if [ $# -ne 1 ] || [ ! -d "$1" ]; then
  echo "usage: scan.sh <repo folder>" >&2
  exit 2
fi
if [ -e "$1/.gitleaksignore" ]; then
  echo ".gitleaksignore: not allowed, the central check does not honor it. Delete it, and ask the org owners to allowlist a false positive in the org config."
  exit 1
fi
max_archive_depth=8
here=$(cd "$(dirname "$0")" && pwd)
exec gitleaks dir "$1" --config "$here/gitleaks.toml" --gitleaks-ignore-path "$here" \
  --max-archive-depth "$max_archive_depth" --ignore-gitleaks-allow \
  --no-banner --no-color --redact --verbose --exit-code 1

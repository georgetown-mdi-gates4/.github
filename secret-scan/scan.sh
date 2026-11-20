#!/bin/sh
# Scan every file in a folder for secrets with gitleaks (dir mode, so the
# files on disk, not git history). Prints rule id, file and line for each
# finding. Secret values are redacted. Uses gitleaks' built-in rules.
# Exit 0 clean, 1 finding, 2 bad usage, other on a gitleaks error.
#
# Run: sh secret-scan/scan.sh <repo folder>
if [ $# -ne 1 ] || [ ! -d "$1" ]; then
  echo "usage: scan.sh <repo folder>" >&2
  exit 2
fi
exec gitleaks dir "$1" --no-banner --no-color --redact --verbose --exit-code 1

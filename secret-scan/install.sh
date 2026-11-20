#!/bin/sh
# Download the pinned gitleaks release (linux_x64, the CI runner) into a
# folder. Stops before it extracts anything unless the download matches
# the pinned sha256. The version and sha256 live in gitleaks-release.env
# beside this script. On success it prints the folder, for $GITHUB_PATH.
#
# Run: sh secret-scan/install.sh <folder>
set -eu
if [ $# -ne 1 ]; then
  echo "usage: install.sh <folder>" >&2
  exit 2
fi
here=$(cd "$(dirname "$0")" && pwd)
. "$here/gitleaks-release.env"
tarball="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -sSfL -o "$tmp/$tarball" \
  "https://github.com/gitleaks/gitleaks/releases/download/v$GITLEAKS_VERSION/$tarball"
(cd "$tmp" && echo "$GITLEAKS_SHA256  $tarball" | sha256sum -c - >&2)
tar -xzf "$tmp/$tarball" -C "$tmp" gitleaks
mkdir -p "$1"
mv "$tmp/gitleaks" "$1/gitleaks"
cd "$1" && pwd

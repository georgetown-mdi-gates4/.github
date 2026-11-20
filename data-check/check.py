"""Reject data files and large files in a repo folder.

Walks the whole tree (skips the folders in rules.json "skip_folders"),
prints one line per rejected file as "<relative path>: <reason>", sorted.
Exit 0 when clean, 1 when anything is rejected, 2 on bad usage.
The rules live in rules.json beside this script.

Run: python3 data-check/check.py <repo folder>
"""
import json
import os
import sys

RULES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")


def reasons(rel, size, rules):
    parts = rel.split("/")
    out = []
    if size > rules["max_bytes"]:
        out.append(f"over {rules['max_bytes']} bytes")
    in_allowed = rel.startswith(rules["allowed_folder"].rstrip("/") + "/")
    in_data = any(p in rules["data_folders"] for p in parts[:-1])
    ext = os.path.splitext(parts[-1])[1].lower()
    if ext in rules["data_extensions"] and in_data and not in_allowed:
        out.append(f"data file type under a {' or '.join(rules['data_folders'])} folder")
    return out


def check(root, rules):
    rejected = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in rules["skip_folders"]]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            why = reasons(rel, os.lstat(path).st_size, rules)
            if why:
                rejected.append(f"{rel}: {'; '.join(why)}")
    return sorted(rejected)


def main(argv):
    if len(argv) != 2 or not os.path.isdir(argv[1]):
        print("usage: check.py <repo folder>", file=sys.stderr)
        return 2
    with open(RULES) as f:
        rules = json.load(f)
    lines = check(argv[1], rules)
    for line in lines:
        print(line)
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

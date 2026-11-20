"""Reject data files and large files in a repo folder.

Walks the whole tree (skips the folders in rules.json "skip_folders"),
prints one line per rejected file as "<relative path>: <reason>", sorted.
A folder or file it cannot read is rejected too ("<path>: cannot read (...)").
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
    in_data = any(p.lower() in rules["data_folders"] for p in parts[:-1])
    ext = os.path.splitext(parts[-1])[1].lower()
    if ext in rules["data_extensions"] and in_data and not in_allowed:
        out.append(f"data file type under a {' or '.join(rules['data_folders'])} folder")
    return out


def check(root, rules):
    rejected = []

    def rel(path):
        return os.path.relpath(path, root).replace(os.sep, "/")

    def unreadable(err):
        rejected.append(f"{rel(err.filename)}: cannot read ({err.strerror})")

    for dirpath, dirnames, filenames in os.walk(root, onerror=unreadable):
        dirnames[:] = [d for d in dirnames if d not in rules["skip_folders"]]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                size = os.lstat(path).st_size
            except OSError as err:
                unreadable(err)
                continue
            why = reasons(rel(path), size, rules)
            if why:
                rejected.append(f"{rel(path)}: {'; '.join(why)}")
    return sorted(rejected)


def main(argv):
    if len(argv) != 2 or not os.path.isdir(argv[1]):
        print("usage: check.py <repo folder>", file=sys.stderr)
        return 2
    with open(RULES) as f:
        rules = json.load(f)
    for key in ("data_folders", "data_extensions"):
        rules[key] = [v.lower() for v in rules[key]]
    lines = check(argv[1], rules)
    for line in lines:
        print(line)
    return 1 if lines else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

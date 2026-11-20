# Backfill: missing README and .gitignore

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
If an earlier `--apply` run stopped after it made the branch, later runs
print "Reference already exists" for that repo. Delete that branch in the
target repo, then run again.
The branch name, PR title and file list live in `backfill/config.json`.
The file contents and the PR body live in `backfill/templates/`.

Run its tests:

    python3 -m unittest discover -s backfill -v

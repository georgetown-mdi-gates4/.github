# .github

This repo holds the shared defaults for the GitHub organization of Georgetown McCourt School's Massive Data Institute. GitHub uses these defaults in every repo in the organization that has no file of the same type of its own. So an edit here applies to all of those repos at once.

- `CONTRIBUTING.md` is the org standard: the rules for every repo, and the commands to check a repo against them.
- `AGENTS.md` is for anyone who changes this repo: how to test it and what it must never hold.
- `GLOSSARY.md` defines the terms these files use.
- `.github/pull_request_template.md` is the default PR body.
- `.github/CODEOWNERS` names one of the org owners as the reviewer for every file in this repo. Only the org owners can change this repo.
- `.github/workflows/data-check.yml` is the central check. The organization rule runs it on every PR. It runs the data check and then the secret scan.
- `data-check/` rejects data files and large files. See `data-check/README.md`.
- `secret-scan/` scans a repo for secrets with a pinned gitleaks and config. See `secret-scan/README.md`.
- `backfill/` is a script an org owner runs by hand. It opens a PR in each repo that has no README or no `.gitignore`. See `backfill/README.md`.

# .github

This repo holds the shared defaults for the GitHub organization of Georgetown McCourt School's Massive Data Institute. GitHub uses these defaults in every repo in the organization that has no file of the same type of its own. So an edit here applies to all of those repos at once.

- `CONTRIBUTING.md` is the org standard: the rules for every repo, and the commands to check a repo against them.
- `.github/pull_request_template.md` is the default PR body.
- `.github/workflows/data-check.yml` is the central check. The organization rule runs it on every PR.
- `data-check/` holds the data and large-file check, with its rules in `data-check/rules.json`.
- `GLOSSARY.md` defines the terms these files use.
- `.github/CODEOWNERS` names one of the org owners as the reviewer for every file in this repo. Only the org owners can change this repo.
- `AGENTS.md` is for anyone who changes this repo: how to test it and what it must never hold.

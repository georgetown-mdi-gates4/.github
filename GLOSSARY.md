# Glossary

**Org standard**: The rules for every repo in this organization except forks, written in this repo's `CONTRIBUTING.md`.
_Avoid_: policy, guidelines, conventions.

**Central check**: The one automated check that runs on every PR in every repo except forks. It rejects secrets, large files, and data files outside the allowed folder.
_Avoid_: CI gate, linter, scanner.

**Allowed folder**: The `tests/fixtures/` folder at the repo root, where small data files for tests may live. Its name matches only in exact case, while the `data` and `index` folder names match in any case, e.g. `Data/survey.csv` fails.
_Avoid_: whitelist, exempt folder, data folder.

**Backfill**: A pass that an org owner runs by hand to add a missing README or `.gitignore` to existing repos. It opens one PR in each repo that lacks a file. The owner of that repo reviews and merges the PR.
_Avoid_: migration, sync, bulk update.

# Glossary

**Org standard**: The set of rules for every repo in this organization except forks, written in `CONTRIBUTING.md`. GitHub shows this written standard in repos that have no `CONTRIBUTING.md` of their own. The organization rule and the central check apply to every repo except forks, whatever its own files say.
_Avoid_: policy, guidelines, conventions.

**Central check**: The one automated check that runs on every PR in every repo except forks. It fails when it finds a secret, a file over 1 MB, or a data file in a place where data is not allowed.
_Avoid_: CI gate, linter, scanner.

**Allowed folder**: The `tests/fixtures/` folder at the repo root, where small data files for tests may live. Each file in it must still be under 1 MB.
_Avoid_: whitelist, exempt folder, data folder.

**Backfill**: A pass the owner runs by hand that adds a missing README or `.gitignore` to existing repos, through one PR per repo that its owner reviews and merges. A second run skips repos that already have an open backfill PR.
_Avoid_: migration, sync, bulk update.

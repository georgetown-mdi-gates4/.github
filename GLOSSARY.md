# Glossary

**Org standard**: The set of rules every repo in this organization follows, written in `CONTRIBUTING.md`. It applies to any repo that has no `CONTRIBUTING.md` of its own.
_Avoid_: policy, guidelines, conventions.

**Central check**: The one automated check that runs on every PR in every repo of the organization. It fails when it finds a secret, a file over 1 MB, or a data file in a place where data is not allowed.
_Avoid_: CI gate, linter, scanner.

**Allowed folder**: The `tests/fixtures/` folder, where small data files for tests may live. Each file in it must still be under 1 MB.
_Avoid_: whitelist, exempt folder, data folder.

**Backfill**: A one-time pass that adds a missing README or `.gitignore` to existing repos, through one PR per repo that its owner reviews and merges.
_Avoid_: migration, sync, bulk update.

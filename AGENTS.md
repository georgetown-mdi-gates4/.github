# Working on this repo

This repo, `georgetown-mdi-gates4/.github`, is public. It holds the organization's default files and the central check. GitHub applies its defaults to every repo in the organization that has no file of its own. So each change here reaches all of those repos at once.

`CONTRIBUTING.md` is the org standard and its single source of truth. GitHub links to it from every org repo that has no `CONTRIBUTING.md` of its own, and the backfill PRs link to it by this URL. So keep the file at this path: `https://github.com/georgetown-mdi-gates4/.github/blob/main/CONTRIBUTING.md`. `CONTRIBUTING.md` quotes the 1 MB limit from `data-check/rules.json`. When you change a value in `rules.json`, update `CONTRIBUTING.md` in the same PR. When you change what `secret-scan/scan.sh` reads or skips, update `CONTRIBUTING.md` and `secret-scan/README.md` in the same PR. Also update `GLOSSARY.md` when it names the folders or files that you changed.

## Work loop

1. Start from an issue in this repo: `gh issue list --repo georgetown-mdi-gates4/.github`. Done when you can name the issue and its acceptance criteria.
2. Make a branch from `main`, e.g. `docs/glossary-terms`. Every change reaches `main` through a PR. Never push to `main`.
3. Run every test suite below. Done when each one ends with `OK`.
4. Open a PR that names the issue, and fill in both fields of the PR template.
5. Get a review from someone who did not write the change, human or agent. Merge only after that review finds nothing blocking.

## Tests

Run from the repo root:

```sh
python3 -m unittest discover -s data-check -v
REQUIRE_GITLEAKS=1 python3 -m unittest discover -s secret-scan -v
python3 -m unittest discover -s backfill -v
```

The secret-scan tests need gitleaks on PATH, at the version in `secret-scan/gitleaks-release.env`. `secret-scan/README.md` says how to get it. Without `REQUIRE_GITLEAKS=1`, the scan tests skip when gitleaks is missing.

When you edit `secret-scan/gitleaks.toml`, set `GITLEAKS_CONFIG_SHA256` in `secret-scan/gitleaks-release.env` in the same PR, or the tests fail. The value is the first field of `sha256sum secret-scan/gitleaks.toml` (on macOS, `shasum -a 256 secret-scan/gitleaks.toml`). Each folder's README has the detail: `data-check/README.md`, `secret-scan/README.md`, `backfill/README.md`.

## Guardrails

This repo is public. Write only text that is safe for anyone to read: the org standard, the check code, and fake test data.

- Leave out partner names, names of people, content from private repos, cloud project IDs and billing details. A GitHub handle in `.github/CODEOWNERS` is the one exception.
- Build each fake secret at test time, in a temporary folder. Never commit a string shaped like a secret, real or fake.
- Run the backfill script without `--apply` to see its plan. Never run it with `--apply` unless an org owner asks for it in that session.
- Name the institute "Georgetown McCourt School's Massive Data Institute" once in a file, then "MDI".
- Use no em-dashes. Check with `grep -rn "$(printf '\342\200\224')" . --exclude-dir=.git`, which must print nothing. It works in sh, bash and zsh.

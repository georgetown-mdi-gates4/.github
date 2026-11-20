# .github

This repo holds the shared defaults for the GitHub organization of
Georgetown McCourt School's Massive Data Institute.

- `data-check/`: the data file check. It rejects data files and large
  files. See `data-check/README.md`.
- `secret-scan/`: the secret scan, gitleaks with a pinned version and
  config. See `secret-scan/README.md`.
- `.github/workflows/data-check.yml`: the workflow that runs both checks
  on every pull request of a repo when the org ruleset requires it.
- `backfill/`: a script the org owner runs by hand. It opens a PR in
  each repo that has no README or no `.gitignore`. See
  `backfill/README.md`.

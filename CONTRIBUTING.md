# Org standard

These rules apply to every repo in this organization except forks. Follow them for every change. A repo can add its own `CONTRIBUTING.md`, and GitHub then shows that page instead of this one. The organization rule and the central check still apply to that repo.

## How a change reaches `main`

Every change reaches `main` through a branch and a pull request (PR).

1. Make a branch from `main`, e.g. `fix/broken-download-link`.
2. Do the steps in "Before you open a PR" below.
3. Push the branch and open a PR into `main`. Fill in both fields of the PR template.
4. The PR can merge with 0 approvals once the central check passes.

An organization rule blocks direct pushes and force-pushes to `main`.

## Before you open a PR

Do each step on your branch. A step is done when its check holds.

1. **One change.** The PR does one thing, and a reader can review it in a few minutes. Split a large change into PRs that each work on their own. Done when every changed file serves the one change that the PR title names.
2. **Tests.** When you change how code behaves, add or update a test for it in the same PR. Done when the tests near your change pass, run with the test command from the repo's README.
3. **README.** The repo's README says what the repo does in one or two sentences, how to run it as commands you can paste, how to get the data if it needs any, and who owns it. Done when the README has all four.
4. **Data check.** Run it from the root of your repo, as shown in "Run the central check locally". Done when it exits 0. If it prints files, move each one as "Data and large files" says.
5. **Secret scan.** Run it from the root of your repo, as shown in "Run the central check locally". Done when it exits 0. If it finds a secret, follow "Secrets".
6. **PR template.** Done when "What changed and why" names the change and its reason, and "How I checked it" lists the commands you ran and what they printed.

## Run the central check locally

Get the check scripts from this repo. When the copy already exists, `git clone` reports that the folder exists, and the command updates the copy instead.

```sh
ORG_CHECK="${TMPDIR:-/tmp}/org-check"
git clone --depth 1 https://github.com/georgetown-mdi-gates4/.github "$ORG_CHECK" || git -C "$ORG_CHECK" pull --ff-only
```

Then run each check from the root of your repo:

```sh
python3 "$ORG_CHECK/data-check/check.py" .
sh "$ORG_CHECK/secret-scan/scan.sh" .
```

Each names every file it rejects and exits 0 when clean, 1 when it finds a problem, 2 on bad usage. The secret scan needs [gitleaks](https://github.com/gitleaks/gitleaks/releases) on your PATH, at the version set by `GITLEAKS_VERSION` in `$ORG_CHECK/.github/workflows/data-check.yml`.

## Data and large files

Keep data in cloud storage. The README says where it is and gives the command that copies it to your machine. Build output (indexes, PDFs, compiled files) is made again from the code, so it stays out of git too.

The central check reads the whole repo on every PR. It fails on:

- **Size**: any file over 1 MB (1,048,576 bytes), anywhere in the repo, e.g. a 40 MB model file.
- **Type**: a data file type under any folder named `data` or `index`, at any depth, e.g. `data/raw/survey.csv` or `src/index/vectors.npy`. The folder name matches in any case, so `Data/survey.csv` fails. The extension matches in any case, so `.CSV` fails like `.csv`.

The exact size limit, file types and folder names live in [`data-check/rules.json`](data-check/rules.json).

Small test data lives in `tests/fixtures/` at the root of the repo. That folder is exempt from the type rule only, so each file in it must still be 1 MB or less. The name must match exactly, in lower case and at the root. A `tests/fixtures/` folder at a lower level, e.g. `src/tests/fixtures/`, gets no exemption.

Add these lines to `.gitignore`:

```
/data/
/index/
.env
/build/
```

Use your repo's own build output folder in place of `/build/`. The leading `/` keeps the pattern at the root, so `tests/fixtures/data/` and a source package named `data` stay in git.

## Secrets

Keep passwords, API keys and tokens in your local environment, in a `.env` file listed in `.gitignore`, or in the repo's GitHub Actions secrets.

The central check scans every file in the repo with gitleaks and the org config in this repo. The org config is the only config the scan uses. A repo's own `.gitleaks.toml` and its `gitleaks:allow` comments have no effect, and a `.gitleaksignore` file fails the check. For a false positive, ask the org owners to add an allowlist entry to the org config.

If the scan finds a secret:

1. Rotate it first. Revoke the key at its provider and make a new one. Done when the old key no longer works.
2. Then remove it from the files, and put the new key where this section says. Done when the secret scan exits 0.

Rotation comes first because the old key stays in git history and in every clone after you delete it.

# How we work

These rules apply to every repo in this organization except forks. A repo can add its own `CONTRIBUTING.md` to replace this page. The organization rule and the central check still apply to that repo.

## Every change goes through a branch and a PR

- Make a branch, e.g. `fix/broken-download-link`. Push it. Open a pull request (PR) into `main`.
- Direct pushes and force-pushes to `main` are blocked by an organization rule.
- A PR can merge with 0 approvals. The central check must pass first.

## Keep secrets out of git

- Never commit a password, API key, token or `.env` file.
- Put secrets in your local environment or in the repo's GitHub Actions secrets.
- If a secret reaches git, revoke it at once. Deleting the file does not remove it from history.

## Keep data and built files out of git

The central check reads the whole repo on every PR. It fails when it finds:

- any file over 1 MB (1,048,576 bytes), e.g. a 40 MB model file;
- a `.npy`, `.docx`, `.pdf`, `.jsonl`, `.parquet` or `.csv` file under any `data/` or `index/` folder, e.g. `data/raw/survey.csv` or `index/vectors.npy`. The case of the extension does not matter, so `.CSV` also fails.

Small test data is allowed under `tests/fixtures/` at the root of the repo, if each file is under 1 MB. A `tests/fixtures/` folder at a lower level, e.g. `src/tests/fixtures/`, gets no exception.

Keep real data in cloud storage. Say in the README where it is and how to get it, e.g. the command that copies it to your machine. Build output (indexes, PDFs, compiled files) is made again from the code, so leave it out too. Add `data/`, `index/`, `.env` and your build output folder, e.g. `build/`, to `.gitignore`.

## Every repo has a README

The README says, at the least:

- what the repo does, in one or two sentences;
- how to run it, as commands you can paste;
- how to get the data, if it needs any;
- who owns it.

## Tests sit near the change

- When you change how code behaves, add or update a test for it in the same PR.
- Run the tests near your change before you push.

## Keep PRs small

- One PR does one thing. A reader can review it in a few minutes.
- Split a large change into PRs that each work on their own.
- Fill in the PR template: what changed and why, and how you checked it.

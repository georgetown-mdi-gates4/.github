# .github

This repo holds the shared defaults for the GitHub organization of Georgetown McCourt School's Massive Data Institute. GitHub uses these defaults in every repo in this organization (georgetown-mdi-gates4) that has no file of the same type of its own. It links the default `CONTRIBUTING.md` from those repos, and it fills in the default PR template when a PR opens. So an edit here applies to all of them at once.

- `CONTRIBUTING.md` is the org standard: how every change goes through a PR, and what must stay out of git.
- `.github/pull_request_template.md` is the default PR body, with a field for what changed and why and a field for how it was checked.
- `GLOSSARY.md` defines the terms these files use.
- `.github/CODEOWNERS` names the org owner as the reviewer for every file in this repo. Only the organization owners can change it.

The repo must stay public for GitHub to use it as the organization default. So it holds no partner names and no personal details, apart from the owner's GitHub handle in CODEOWNERS. It also holds no private repo content and no cloud or billing details.

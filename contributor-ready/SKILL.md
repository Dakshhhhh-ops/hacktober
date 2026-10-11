---
name: contributor-ready
description: Audits a git repository for how ready it is to receive outside open-source contributions (README setup and usage sections, LICENSE, CONTRIBUTING guide, code of conduct, issue and PR templates, CI, .gitignore), gives it a score out of 100, and drafts the missing files. Use when the user wants to prepare a repo for Hacktoberfest, open-source a project, make it contributor-friendly, add a CONTRIBUTING guide or templates, or asks why nobody contributes to their repo.
license: MIT
compatibility: Requires Python 3.8+ (standard library only, no network access).
metadata:
  author: Dakshhhhh-ops
  version: "1.0"
---

# Contributor Ready

Make a repository easy for a stranger to contribute to. Audit first, then fix the gaps
in order of impact, then audit again to show the improvement.

## Step 1: Audit

Run the bundled script against the repository root:

```
python scripts/audit.py <path-to-repo> --json
```

It returns a `score` (0-100), a `grade`, and a list of `checks`. Each check has
`id`, `title`, `weight`, `passed`, `detail`, and a `fix` hint. Drop `--json` for a
human-readable report.

## Step 2: Report

Tell the user the score and grade, then list the failing checks, highest weight first.
Keep it to one line per check. Do not list the passing checks unless asked.

## Step 3: Fix, highest weight first

Before writing anything, read the repository so the fixes are real:

- Find the actual install, run and test commands from `package.json`, `pyproject.toml`,
  `requirements.txt`, `Makefile`, `Cargo.toml`, `go.mod` or the CI workflow.
- If a command cannot be found, leave a clearly marked `TODO` and tell the user.
  Never invent a command.

Per check:

| Check id | What to do |
| --- | --- |
| `readme`, `readme_setup`, `readme_usage` | Add or extend the README: what the project does, setup steps, a usage example. |
| `license` | Ask the user which license they want. Do not choose one for them. |
| `contributing` | Fill in [assets/CONTRIBUTING.md](assets/CONTRIBUTING.md) and save it as `CONTRIBUTING.md`. |
| `code_of_conduct` | Offer the Contributor Covenant and ask for a contact email. |
| `issue_templates` | Copy [assets/bug_report.md](assets/bug_report.md) to `.github/ISSUE_TEMPLATE/bug_report.md`. |
| `pr_template` | Copy [assets/PULL_REQUEST_TEMPLATE.md](assets/PULL_REQUEST_TEMPLATE.md) to `.github/PULL_REQUEST_TEMPLATE.md`. |
| `ci` | Propose a minimal workflow that runs the existing tests. Skip if there are no tests. |
| `gitignore` | Add a `.gitignore` that matches the project's language. |

Replace every `{{PLACEHOLDER}}` in a template. A file with a placeholder left in it is
not finished.

## Step 4: Re-audit

Run the script again and report the score before and after.

## Rules

- Never overwrite an existing file. Extend it, or show the user a diff first.
- Show the user the list of files you are going to create before creating them.
- Do not commit or push unless the user asks.
- A high score is not the goal. If a check does not fit the project (for example CI on
  a docs-only repo), say so and skip it.

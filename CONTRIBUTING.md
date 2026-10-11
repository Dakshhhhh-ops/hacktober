# Contributing to contributor-ready

Thanks for wanting to help. This guide gets you from zero to an open pull request.

## Set up the project

You need Python 3.8 or newer. There is nothing to install.

```
git clone https://github.com/Dakshhhhh-ops/hacktober.git
cd hacktober
```

## Check your change

There is no test suite yet. Run the audit against this repository and make sure it still
works in both output modes:

```
python contributor-ready/scripts/audit.py .
python contributor-ready/scripts/audit.py . --json
```

## Make a change

1. Fork the repository and create a branch: `git checkout -b add-changelog-check`
2. Make your change. Keep each pull request to one topic.
3. Run the two commands above.
4. Commit with a message that says what changed and why.
5. Push your branch and open a pull request against `main`.

## What makes a good pull request

- It solves one problem and says which issue it closes.
- It explains how you checked it works.
- It does not reformat unrelated code.
- `audit.py` stays standard library only, so the skill runs anywhere Python does.

## Ideas to work on

- New checks, for example a changelog, a security policy, or `good first issue` labels.
- Templates for more issue types in `contributor-ready/assets/`.
- Unit tests for `audit.py`.

## Getting help

Open an issue on the repository.

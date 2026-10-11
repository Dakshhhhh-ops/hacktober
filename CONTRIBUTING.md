# Contributing to contributor-ready

Thanks for wanting to help. This guide gets you from zero to an open pull request.

## Set up the project

You need Python 3.8 or newer. There is nothing to install.

```
git clone https://github.com/Dakshhhhh-ops/hacktober.git
cd hacktober
```

To work on the web checker you also need Node.js 20 or newer:

```
cd web
npm install
npm run dev
```

## Check your change

For the skill, run the audit against this repository and make sure it still works in
both output modes:

```
python contributor-ready/scripts/audit.py .
python contributor-ready/scripts/audit.py . --json
```

For the web checker, run the unit tests and a build from the `web` folder:

```
npm test
npm run build
```

## Make a change

1. Fork the repository and create a branch: `git checkout -b add-changelog-check`
2. Make your change. Keep each pull request to one topic.
3. Run the checks above for the part you changed.
4. Commit with a message that says what changed and why.
5. Push your branch and open a pull request against `main`.

## What makes a good pull request

- It solves one problem and says which issue it closes.
- It explains how you checked it works.
- It does not reformat unrelated code.
- `audit.py` stays standard library only, so the skill runs anywhere Python does.
- A change to a check is made in both `contributor-ready/scripts/audit.py` and
  `web/src/lib/audit.js`, so the skill and the web page give the same score.
- A change under `web/` passes `npm test`, and the rebuilt `docs/` folder
  (`npm run build`) is committed with it.

## Ideas to work on

- New checks, for example a changelog, a security policy, or `good first issue` labels.
- Templates for more issue types in `contributor-ready/assets/`.
- Unit tests for `audit.py`, to match the ones for the web version.

## Getting help

Open an issue on the repository.

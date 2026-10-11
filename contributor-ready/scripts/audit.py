#!/usr/bin/env python3
"""Audit a repository for how ready it is to receive outside contributions.

Usage: python audit.py [repo_path] [--json]
Standard library only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

DOC_DIRS = ("", ".github", "docs")
HEADING = re.compile(r"^#{1,6}\s*(.+)$", re.MULTILINE)
SETUP_WORDS = ("install", "setup", "set up", "getting started", "quick start", "quickstart")
USAGE_WORDS = ("usage", "example", "how to use", "demo", "running")


def find_doc(repo, stems):
    """Return the first file in the usual doc locations whose stem matches."""
    for d in DOC_DIRS:
        base = repo / d if d else repo
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if p.is_file() and p.stem.lower() in stems:
                return p
    return None


def has_heading(text, words):
    return any(w in h.lower() for h in HEADING.findall(text) for w in words)


def has_files(directory, patterns=("*",)):
    return directory.is_dir() and any(
        p.is_file() for pat in patterns for p in directory.glob(pat)
    )


def audit(repo):
    checks = []

    def add(id_, title, weight, passed, detail, fix):
        checks.append({
            "id": id_, "title": title, "weight": weight,
            "passed": bool(passed), "detail": detail, "fix": fix,
        })

    def rel(p):
        return p.relative_to(repo).as_posix()

    readme = find_doc(repo, {"readme"})
    text = readme.read_text(encoding="utf-8", errors="replace") if readme else ""
    words = len(text.split())
    add("readme", "README explains the project", 15, words >= 50,
        f"{rel(readme)} has {words} words" if readme else "no README found",
        "Write a README of at least a few paragraphs: what it does and who it is for.")
    add("readme_setup", "README has setup instructions", 15, has_heading(text, SETUP_WORDS),
        "looked for a heading like Installation, Setup or Getting Started",
        "Add a setup section with the exact commands to install and run.")
    add("readme_usage", "README has a usage example", 10, has_heading(text, USAGE_WORDS),
        "looked for a heading like Usage, Examples or Demo",
        "Add a usage section with one example a newcomer can copy and run.")

    lic = find_doc(repo, {"license", "licence", "copying", "unlicense"})
    add("license", "Open-source license", 20, lic,
        rel(lic) if lic else "no LICENSE file found",
        "Add a LICENSE file. Without one, nobody may legally reuse the code.")

    contrib = find_doc(repo, {"contributing"})
    add("contributing", "CONTRIBUTING guide", 15, contrib,
        rel(contrib) if contrib else "no CONTRIBUTING file found",
        "Add CONTRIBUTING.md from assets/CONTRIBUTING.md.")

    coc = find_doc(repo, {"code_of_conduct", "code-of-conduct"})
    add("code_of_conduct", "Code of conduct", 5, coc,
        rel(coc) if coc else "no CODE_OF_CONDUCT file found",
        "Add CODE_OF_CONDUCT.md, for example the Contributor Covenant.")

    gh = repo / ".github"
    issues = has_files(gh / "ISSUE_TEMPLATE") or find_doc(repo, {"issue_template"})
    add("issue_templates", "Issue template", 5, issues,
        "found" if issues else "no .github/ISSUE_TEMPLATE/ found",
        "Add .github/ISSUE_TEMPLATE/bug_report.md from assets/bug_report.md.")

    pr = has_files(gh / "PULL_REQUEST_TEMPLATE") or find_doc(repo, {"pull_request_template"})
    add("pr_template", "Pull request template", 5, pr,
        "found" if pr else "no pull request template found",
        "Add .github/PULL_REQUEST_TEMPLATE.md from assets/PULL_REQUEST_TEMPLATE.md.")

    ci = (has_files(gh / "workflows", ("*.yml", "*.yaml"))
          or (repo / ".gitlab-ci.yml").is_file()
          or (repo / ".circleci" / "config.yml").is_file())
    add("ci", "Continuous integration", 5, ci,
        "found" if ci else "no CI configuration found",
        "Add a workflow that runs the tests on every pull request.")

    gitignore = (repo / ".gitignore").is_file()
    add("gitignore", ".gitignore", 5, gitignore,
        "found" if gitignore else "no .gitignore found",
        "Add a .gitignore that matches the project's language.")

    total = sum(c["weight"] for c in checks)
    score = round(100 * sum(c["weight"] for c in checks if c["passed"]) / total)
    grade = "ready" if score >= 85 else "almost ready" if score >= 60 else "not ready"
    return {"repo": str(repo), "score": score, "grade": grade, "checks": checks}


def print_report(result):
    print(f"Contributor readiness: {result['score']}/100 ({result['grade']})")
    print(f"Repository: {result['repo']}\n")
    for c in result["checks"]:
        mark = "PASS" if c["passed"] else "FAIL"
        print(f"  [{mark}] {c['title']} ({c['weight']} pts) - {c['detail']}")
    failing = sorted((c for c in result["checks"] if not c["passed"]),
                     key=lambda c: -c["weight"])
    if failing:
        print("\nFix next, biggest win first:")
        for c in failing:
            print(f"  +{c['weight']:>2}  {c['fix']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", default=".", help="path to the repository root")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        sys.exit(f"error: {repo} is not a directory")

    result = audit(repo)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()

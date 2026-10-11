import test from "node:test";
import assert from "node:assert/strict";
import { audit, parseRepo, toMarkdown } from "./audit.js";

const README = `# Demo\n\n${"word ".repeat(60)}\n\n## Installation\n\nnpm install\n\n## Usage\n\nnpm start\n`;

test("parseRepo accepts owner/name and GitHub URLs", () => {
  assert.deepEqual(parseRepo("pallets/flask"), { owner: "pallets", name: "flask" });
  assert.deepEqual(parseRepo("https://github.com/pallets/flask/tree/main"), { owner: "pallets", name: "flask" });
  assert.deepEqual(parseRepo("git@github.com:pallets/flask.git"), { owner: "pallets", name: "flask" });
  assert.equal(parseRepo("nonsense"), null);
  assert.equal(parseRepo("a b/c"), null);
});

test("an empty repository scores 0", () => {
  const r = audit([], "");
  assert.equal(r.score, 0);
  assert.equal(r.grade, "not ready");
  assert.equal(r.checks.length, 10);
});

test("a complete repository scores 100", () => {
  const paths = [
    "README.md", "LICENSE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", ".gitignore",
    ".github/ISSUE_TEMPLATE/bug_report.md", ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml", "src/index.js",
  ];
  const r = audit(paths, README);
  assert.equal(r.score, 100);
  assert.equal(r.grade, "ready");
});

test("docs are found in .github and docs, but not deeper", () => {
  const found = audit(["docs/contributing.rst", ".github/CODE_OF_CONDUCT.md"], "");
  assert.equal(found.checks.find((c) => c.id === "contributing").passed, true);
  assert.equal(found.checks.find((c) => c.id === "code_of_conduct").passed, true);

  const nested = audit(["packages/app/LICENSE"], "");
  assert.equal(nested.checks.find((c) => c.id === "license").passed, false);
});

test("a short README fails the first check", () => {
  const r = audit(["README.md"], "# Demo");
  assert.equal(r.checks.find((c) => c.id === "readme").passed, false);
});

test("toMarkdown lists failing checks, biggest first", () => {
  const md = toMarkdown(audit(["README.md"], README));
  const lines = md.split("\n").filter((l) => l.startsWith("- [ ]"));
  assert.match(lines[0], /Open-source license/);
  assert.equal(lines.length, 7);
});

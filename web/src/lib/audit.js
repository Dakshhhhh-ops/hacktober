// Browser port of contributor-ready/scripts/audit.py. Keep the checks in sync.

const DOC_DIRS = ["", ".github", "docs"];
const HEADING = /^#{1,6}\s*(.+)$/gm;
const SETUP_WORDS = ["install", "setup", "set up", "getting started", "quick start", "quickstart"];
const USAGE_WORDS = ["usage", "example", "how to use", "demo", "running"];

export function parseRepo(input) {
  const s = String(input).trim()
    .replace(/^(https?:\/\/)?(www\.)?github\.com\//i, "")
    .replace(/^git@github\.com:/i, "");
  const [owner, rawName] = s.split(/[/?#]/);
  const name = (rawName || "").replace(/\.git$/, "");
  const ok = /^[\w.-]+$/;
  return owner && name && ok.test(owner) && ok.test(name) ? { owner, name } : null;
}

function dirOf(path) {
  const i = path.lastIndexOf("/");
  return i < 0 ? "" : path.slice(0, i);
}

function stemOf(path) {
  const base = path.slice(path.lastIndexOf("/") + 1);
  const i = base.lastIndexOf(".");
  return (i > 0 ? base.slice(0, i) : base).toLowerCase();
}

// First file in the usual doc locations whose stem matches.
function findDoc(paths, stems) {
  for (const d of DOC_DIRS) {
    const hit = paths.filter((p) => dirOf(p) === d && stems.includes(stemOf(p))).sort()[0];
    if (hit) return hit;
  }
  return null;
}

function hasHeading(text, words) {
  return [...text.matchAll(HEADING)].some((m) => words.some((w) => m[1].toLowerCase().includes(w)));
}

function hasFiles(paths, dir, pattern) {
  return paths.some((p) => dirOf(p).toLowerCase() === dir.toLowerCase() && (!pattern || pattern.test(p)));
}

// paths: every file path in the repo. readmeText: contents of the README, or "".
export function audit(paths, readmeText) {
  const checks = [];
  const add = (id, title, weight, passed, detail, fix) =>
    checks.push({ id, title, weight, passed: Boolean(passed), detail, fix });

  const readme = findDoc(paths, ["readme"]);
  const text = readme ? readmeText || "" : "";
  const words = text.split(/\s+/).filter(Boolean).length;
  add("readme", "README explains the project", 15, words >= 50,
    readme ? `${readme} has ${words} words` : "no README found",
    "Write a README of at least a few paragraphs: what it does and who it is for.");
  add("readme_setup", "README has setup instructions", 15, hasHeading(text, SETUP_WORDS),
    "looked for a heading like Installation, Setup or Getting Started",
    "Add a setup section with the exact commands to install and run.");
  add("readme_usage", "README has a usage example", 10, hasHeading(text, USAGE_WORDS),
    "looked for a heading like Usage, Examples or Demo",
    "Add a usage section with one example a newcomer can copy and run.");

  const lic = findDoc(paths, ["license", "licence", "copying", "unlicense"]);
  add("license", "Open-source license", 20, lic, lic || "no LICENSE file found",
    "Add a LICENSE file. Without one, nobody may legally reuse the code.");

  const contrib = findDoc(paths, ["contributing"]);
  add("contributing", "CONTRIBUTING guide", 15, contrib, contrib || "no CONTRIBUTING file found",
    "Add a CONTRIBUTING.md that covers setup, tests and how to open a pull request.");

  const coc = findDoc(paths, ["code_of_conduct", "code-of-conduct"]);
  add("code_of_conduct", "Code of conduct", 5, coc, coc || "no CODE_OF_CONDUCT file found",
    "Add CODE_OF_CONDUCT.md, for example the Contributor Covenant.");

  const issues = hasFiles(paths, ".github/ISSUE_TEMPLATE") || findDoc(paths, ["issue_template"]);
  add("issue_templates", "Issue template", 5, issues,
    issues ? "found" : "no .github/ISSUE_TEMPLATE/ found",
    "Add a bug report template in .github/ISSUE_TEMPLATE/.");

  const pr = hasFiles(paths, ".github/PULL_REQUEST_TEMPLATE") || findDoc(paths, ["pull_request_template"]);
  add("pr_template", "Pull request template", 5, pr,
    pr ? "found" : "no pull request template found",
    "Add .github/PULL_REQUEST_TEMPLATE.md with a short checklist.");

  const ci = hasFiles(paths, ".github/workflows", /\.ya?ml$/)
    || paths.includes(".gitlab-ci.yml")
    || paths.includes(".circleci/config.yml");
  add("ci", "Continuous integration", 5, ci, ci ? "found" : "no CI configuration found",
    "Add a workflow that runs the tests on every pull request.");

  const gitignore = paths.includes(".gitignore");
  add("gitignore", ".gitignore", 5, gitignore, gitignore ? "found" : "no .gitignore found",
    "Add a .gitignore that matches the project's language.");

  const total = checks.reduce((n, c) => n + c.weight, 0);
  const earned = checks.reduce((n, c) => n + (c.passed ? c.weight : 0), 0);
  const score = Math.round((100 * earned) / total);
  const grade = score >= 85 ? "ready" : score >= 60 ? "almost ready" : "not ready";
  return { score, grade, checks, readme };
}

async function api(path) {
  let res;
  try {
    res = await fetch("https://api.github.com" + path, {
      headers: { Accept: "application/vnd.github+json" },
    });
  } catch (e) {
    throw new Error("Could not reach GitHub. Check your connection and try again.");
  }
  if (res.status === 404) throw new Error("Repository not found. It has to be public.");
  if (res.status === 409) throw new Error("This repository is empty.");
  if (res.status === 403 || res.status === 429) {
    throw new Error("GitHub's rate limit was reached. Try again in a few minutes.");
  }
  if (!res.ok) throw new Error(`GitHub returned an error (${res.status}).`);
  return res.json();
}

// Audit a public GitHub repository given "owner/name" or its URL.
export async function auditRepo(input) {
  const repo = parseRepo(input);
  if (!repo) throw new Error("Enter a repository as owner/name or paste its GitHub URL.");
  const slug = `${repo.owner}/${repo.name}`;

  const info = await api(`/repos/${slug}`);
  const branch = info.default_branch;
  const tree = await api(`/repos/${slug}/git/trees/${encodeURIComponent(branch)}?recursive=1`);
  const paths = tree.tree.filter((t) => t.type === "blob").map((t) => t.path);

  let readmeText = "";
  const readme = findDoc(paths, ["readme"]);
  if (readme) {
    const rawPath = [branch, ...readme.split("/")].map(encodeURIComponent).join("/");
    const res = await fetch(`https://raw.githubusercontent.com/${slug}/${rawPath}`).catch(() => null);
    if (res && res.ok) readmeText = await res.text();
  }

  return {
    repo: info.full_name,
    url: info.html_url,
    truncated: Boolean(tree.truncated),
    ...audit(paths, readmeText),
  };
}

// The failing checks as a Markdown task list, ready to paste into a GitHub issue.
export function toMarkdown(result) {
  const failing = result.checks.filter((c) => !c.passed).sort((a, b) => b.weight - a.weight);
  const lines = [
    `## Contributor readiness: ${result.score}/100 (${result.grade})`,
    "",
    ...failing.map((c) => `- [ ] **${c.title}** (+${c.weight}): ${c.fix}`),
  ];
  if (failing.length === 0) lines.push("Every check passes.");
  return lines.join("\n");
}

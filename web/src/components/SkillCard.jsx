import CopyButton from "./CopyButton.jsx";

export default function SkillCard({ repoUrl }) {
  const install = `git clone ${repoUrl}.git\ncp -r hacktober/contributor-ready ~/.claude/skills/`;

  return (
    <section className="card skill">
      <span className="label">Use it inside your coding agent</span>
      <h2>The agent skill</h2>
      <p>
        The same audit ships as a skill built to the Agent Skills open standard. Your agent runs
        it, reads your repo for the real install and test commands, drafts the missing files, and
        audits again to show the difference.
      </p>
      <div className="code">
        <CopyButton text={install} className="copy" />
        <pre>{install}</pre>
      </div>
      <p className="hint">
        Then ask your agent: “Make this repo ready for Hacktoberfest contributors.”
      </p>
    </section>
  );
}

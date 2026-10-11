const EXAMPLES = ["Dakshhhhh-ops/hacktober", "pallets/flask", "octocat/Hello-World"];

export default function AuditForm({ query, onQueryChange, onSubmit, busy, error, recent, onClearRecent }) {
  function handleSubmit(event) {
    event.preventDefault();
    onSubmit(query);
  }

  return (
    <section className="card checker">
      <label className="label" htmlFor="repo">GitHub repository</label>
      <form onSubmit={handleSubmit}>
        <input
          id="repo"
          type="text"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="owner/name or https://github.com/owner/name"
          autoComplete="off"
          autoCapitalize="off"
          spellCheck="false"
          required
        />
        <button className="button" type="submit" disabled={busy} aria-busy={busy}>
          {busy ? "Auditing…" : "Audit"}
        </button>
      </form>

      <div className="examples">
        <span className="label">Try</span>
        {EXAMPLES.map((repo) => (
          <button key={repo} className="chip" type="button" onClick={() => onSubmit(repo)}>
            {repo}
          </button>
        ))}
      </div>

      {recent.length > 0 && (
        <div className="examples">
          <span className="label">Recent</span>
          {recent.map((item) => (
            <button key={item.repo} className="chip" type="button" onClick={() => onSubmit(item.repo)}>
              {item.repo} <span className="chip-score">{item.score}</span>
            </button>
          ))}
          <button className="link-button" type="button" onClick={onClearRecent}>Clear</button>
        </div>
      )}

      <p className="status" role="status" aria-live="polite">{error}</p>
    </section>
  );
}

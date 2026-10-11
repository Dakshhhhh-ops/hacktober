import { useCallback, useEffect, useRef, useState } from "react";
import { auditRepo } from "./lib/audit.js";
import { prefersReducedMotion, useRecentAudits } from "./hooks.js";
import Ticker from "./components/Ticker.jsx";
import AuditForm from "./components/AuditForm.jsx";
import Results from "./components/Results.jsx";
import Steps from "./components/Steps.jsx";
import SkillCard from "./components/SkillCard.jsx";

const REPO_URL = "https://github.com/Dakshhhhh-ops/hacktober";

export default function App() {
  const [query, setQuery] = useState("");
  // status: "idle" | "loading" | "done" | "error"
  const [audit, setAudit] = useState({ status: "idle" });
  const { recent, remember, clear } = useRecentAudits();
  const latestRun = useRef(0);
  const resultsRef = useRef(null);

  const run = useCallback(async (value) => {
    const runId = ++latestRun.current;
    setQuery(value);
    setAudit({ status: "loading" });
    try {
      const result = await auditRepo(value);
      if (runId !== latestRun.current) return;
      setAudit({ status: "done", result, runId });
      remember(result);
      try {
        window.history.replaceState(null, "", "?repo=" + encodeURIComponent(result.repo));
      } catch (e) {
        // Blocked on some file:// pages. The shareable link is a nicety, so ignore it.
      }
    } catch (err) {
      if (runId !== latestRun.current) return;
      setAudit({ status: "error", message: err.message });
    }
  }, [remember]);

  // Run the audit named in a ?repo= link once, on first load.
  const startedFromLink = useRef(false);
  useEffect(() => {
    if (startedFromLink.current) return;
    startedFromLink.current = true;
    const linked = new URLSearchParams(window.location.search).get("repo");
    if (linked) run(linked);
  }, [run]);

  useEffect(() => {
    if (audit.status === "done" && resultsRef.current) {
      resultsRef.current.scrollIntoView({
        behavior: prefersReducedMotion() ? "auto" : "smooth",
        block: "start",
      });
    }
  }, [audit]);

  return (
    <>
      <header className="site-header">
        <div className="wrap">
          <span className="label">contributor-ready</span>
          <a className="label" href={REPO_URL}>GitHub</a>
        </div>
      </header>
      <Ticker />

      <main className="wrap">
        <section className="hero">
          <span className="label">Open-source agent skill + repo checker</span>
          <h1>Is your repo <mark>ready</mark> for contributors?</h1>
          <p>
            Paste any public GitHub repository. It gets a score out of 100 for the ten things a
            stranger needs before they can send you a pull request.
          </p>
        </section>

        <AuditForm
          query={query}
          onQueryChange={setQuery}
          onSubmit={run}
          busy={audit.status === "loading"}
          error={audit.status === "error" ? audit.message : ""}
          recent={recent}
          onClearRecent={clear}
        />

        {audit.status === "done" && (
          <Results key={audit.runId} ref={resultsRef} result={audit.result} />
        )}

        <Steps />
        <SkillCard repoUrl={REPO_URL} />
      </main>

      <footer className="site-footer">
        <div className="wrap">
          Built at Hacktoberfest Hack Day Hamirpur x ISTE NITH, October 2026. MIT licensed.
          The look is inspired by Hacktoberfest; this project is not affiliated with it.
        </div>
      </footer>
    </>
  );
}

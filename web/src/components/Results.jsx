import { forwardRef, useState } from "react";
import { toMarkdown } from "../lib/audit.js";
import { useCountUp } from "../hooks.js";
import CopyButton from "./CopyButton.jsx";

function ScoreCard({ result }) {
  const shown = useCountUp(result.score);
  return (
    <div className="card score">
      <div className="score-num">
        {shown}
        <small>/100</small>
      </div>
      <div>
        <a href={result.url}>{result.repo}</a>
        <br />
        <span className={"label tag " + result.grade.split(" ")[0]}>{result.grade}</span>
        <div className="bar" role="img" aria-label={`Score ${result.score} out of 100`}>
          <span style={{ width: result.score + "%" }} />
        </div>
        {result.truncated && (
          <p className="note">
            This repository is very large, so some files may not have been checked.
          </p>
        )}
      </div>
    </div>
  );
}

const FILTERS = [
  { id: "all", label: "All", keep: () => true },
  { id: "failing", label: "Failing", keep: (c) => !c.passed },
  { id: "passing", label: "Passing", keep: (c) => c.passed },
];

function CheckList({ checks }) {
  const [filter, setFilter] = useState("all");
  const visible = checks.filter(FILTERS.find((f) => f.id === filter).keep);

  return (
    <>
      <div className="section-head">
        <h2>The ten checks</h2>
        <div className="tabs" role="group" aria-label="Filter checks">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              className="chip"
              type="button"
              aria-pressed={filter === f.id}
              onClick={() => setFilter(f.id)}
            >
              {f.label} {checks.filter(f.keep).length}
            </button>
          ))}
        </div>
      </div>
      {visible.length === 0 ? (
        <p className="all-good">No checks in this group.</p>
      ) : (
        <ul className="checks" key={filter}>
          {visible.map((c, i) => (
            <li key={c.id} style={{ "--i": i }}>
              <span className={"label tag " + (c.passed ? "pass" : "fail")}>
                {c.passed ? "Pass" : "Fail"}
              </span>
              <div>
                <b>{c.title}</b>
                <span className="detail">{c.detail}</span>
              </div>
              <span className="label pts">{c.weight} pts</span>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function FixList({ result }) {
  const failing = result.checks.filter((c) => !c.passed).sort((a, b) => b.weight - a.weight);

  return (
    <>
      <div className="section-head">
        <h2>Fix next, biggest win first</h2>
        {failing.length > 0 && <CopyButton text={toMarkdown(result)} label="Copy as checklist" />}
      </div>
      {failing.length === 0 ? (
        <p className="all-good">Nothing to fix. This repository passes every check.</p>
      ) : (
        <ol className="fixes">
          {failing.map((c) => (
            <li key={c.id}>
              <span className="pts">+{c.weight}</span>
              <span>{c.fix}</span>
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

const Results = forwardRef(function Results({ result }, ref) {
  return (
    <section className="results" ref={ref}>
      <ScoreCard result={result} />
      <CheckList checks={result.checks} />
      <FixList result={result} />
    </section>
  );
});

export default Results;

const STEPS = [
  { title: "Paste a repo", text: "Any public GitHub repository. No login and nothing to install." },
  { title: "Get a score", text: "Ten checks, weighted by how much each one blocks a new contributor." },
  { title: "Fix the gaps", text: "Work down the list yourself, or let the agent skill draft the files." },
];

export default function Steps() {
  return (
    <section className="steps" aria-labelledby="steps-title">
      <h2 id="steps-title">How it works</h2>
      <ol>
        {STEPS.map((step, i) => (
          <li className="card" key={step.title}>
            <span className="step-num">{i + 1}</span>
            <h3>{step.title}</h3>
            <p>{step.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

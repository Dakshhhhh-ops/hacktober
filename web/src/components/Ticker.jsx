const WORDS = [
  "Open source",
  "Good first issue",
  "Pull requests welcome",
  "Hack Day Hamirpur",
  "ISTE NITH",
  "October 2026",
];

// The list is rendered twice so the scroll loops without a gap.
export default function Ticker() {
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker-track">
        {[...WORDS, ...WORDS].map((word, i) => (
          <span key={i}>{word}</span>
        ))}
      </div>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";

const RECENT_KEY = "contributor-ready:recent";
const RECENT_MAX = 6;

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// Animates a number from 0 to target.
export function useCountUp(target, duration = 700) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (prefersReducedMotion() || target === 0) {
      setValue(target);
      return undefined;
    }
    let frame;
    const start = performance.now();
    const tick = (now) => {
      const t = Math.min((now - start) / duration, 1);
      setValue(Math.round(target * (1 - Math.pow(1 - t, 3))));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return value;
}

function readRecent() {
  try {
    const saved = JSON.parse(localStorage.getItem(RECENT_KEY));
    return Array.isArray(saved) ? saved : [];
  } catch (e) {
    return [];
  }
}

// The last few audited repositories, kept in this browser only.
export function useRecentAudits() {
  const [recent, setRecent] = useState(readRecent);

  useEffect(() => {
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(recent));
    } catch (e) {
      // Storage can be blocked (private windows); the list then lasts for this visit only.
    }
  }, [recent]);

  const remember = useCallback((result) => {
    const entry = { repo: result.repo, score: result.score };
    setRecent((items) => [entry, ...items.filter((i) => i.repo !== entry.repo)].slice(0, RECENT_MAX));
  }, []);

  const clear = useCallback(() => setRecent([]), []);

  return { recent, remember, clear };
}

export { prefersReducedMotion };

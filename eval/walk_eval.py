"""How well does walk mode's object detector do on the labelled photos?

    python eval/walk_eval.py

Walk mode only knows people, bicycles, motorbikes, vehicles and animals, so it is scored
only on labelled hazards of those kinds (see detector.SAME_THING), with walk mode's own
rule for what it says (near anything, or mid distance straight ahead). It also reports
how many clear scenes would get a warning. No vision-language model is used.
"""
import csv
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from drishti import config, detector  # noqa: E402

SETS = {"tuning": ROOT / "eval", "held-out": ROOT / "eval" / "heldout"}


def kind_of(phrase: str) -> str | None:
    """'cows' -> 'animal', 'auto rickshaw' -> 'vehicle', 'stairs' -> None."""
    for kind in detector.SAME_THING:
        if detector._mentions(phrase, kind):
            return kind
    return None


def main() -> None:
    if not detector.available():
        sys.exit(f"The object detector is not installed: {config.DETECTOR_MODEL}")
    lines = ["| Set | Labelled people, vehicles and animals warned about | Clear scenes with a warning | Median time |",
             "| --- | --- | --- | --- |"]
    for name, folder in SETS.items():
        with (folder / "labels.csv").open(newline="", encoding="utf-8-sig") as f:
            rows = [r for r in csv.DictReader(f) if (r.get("hazards_true") or "").strip().lower() != "n/a"]
        caught = total = clear = clear_warned = 0
        times = []
        for row in rows:
            image = (folder / "images" / row["image"]).read_bytes()
            started = time.perf_counter()
            warned = {h.what for h in detector.walk_warnings(detector.detect(image))}
            times.append((time.perf_counter() - started) * 1000)
            required = [item.split("|")[0] for item in row["hazards_true"].split(";")
                        if item.strip() and not item.startswith("?")]
            kinds = [kind_of(label) for label in required]
            for label, kind in zip(required, kinds):
                if kind:
                    total += 1
                    hit = kind in warned
                    caught += hit
                    print(f"  {row['image']}: {label} ({kind}) {'warned' if hit else 'MISSED'}")
            if not required:
                clear += 1
                clear_warned += bool(warned)
                if warned:
                    print(f"  {row['image']}: clear scene, but warned about {sorted(warned)}")
        lines.append(f"| {name} | {caught} of {total} | {clear_warned} of {clear} | "
                     f"{statistics.median(times):.0f} ms |")
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()

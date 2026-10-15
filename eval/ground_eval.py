"""Ground hazards only: how many does the vision model find?

    python eval/ground_eval.py --set heldout

Walk mode's ground check is the Surroundings answer with people, vehicles and animals
removed (the object detector warns about those), so that is what is scored by default.

Scores only labelled hazards on the ground (holes, drains, steps, kerbs, water, broken
paving); people, vehicles and animals are walk mode's detector's job and do not count
here, either way. A ground hazard the model reports that matches no label is a false
alarm. Uses the same image resizing as the page (768 px).
"""
import argparse
import base64
import csv
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT))

from drishti import config, detector, vlm  # noqa: E402
from run_eval import match_hazards, parse_hazard_labels, shrink  # noqa: E402

SETS = {"tuning": ROOT / "eval", "heldout": ROOT / "eval" / "heldout"}
GROUND_WORDS = ("hole", "pothole", "pit", "crater", "drain", "manhole", "sewer", "trench", "ditch",
                "excavation", "puddle", "water", "wet", "slippery", "flood", "mud", "muddy",
                "step", "steps", "stair", "stairs", "staircase", "stairway", "escalator", "kerb",
                "curb", "edge", "ledge", "drop", "uneven", "broken", "crack", "cracked", "raised",
                "pavement", "paving", "road", "track", "tracks", "rail", "rails", "cable", "gap")


def is_ground(phrase: str) -> bool:
    words = phrase.lower().replace("-", " ").split()
    return any(w.rstrip("s") in {g.rstrip("s") for g in GROUND_WORDS} for w in words)


def not_ground(phrase: str) -> bool:
    """People, vehicles and animals: walk mode's detector handles them."""
    return any(detector._mentions(phrase, kind) for kind in detector.SAME_THING)


def score(rows, folder, mode):
    caught = total = clear = clear_warned = false_alarms = 0
    times = []
    for row in rows:
        labels = parse_hazard_labels(row["hazards_true"])
        # Only ground labels are required; everything else is optional (neither hit nor miss).
        ground = [s for s in labels if not s[0].startswith("?") and any(is_ground(x) for x in s)]
        optional = [s if s[0].startswith("?") else ["?" + s[0]] + s[1:] for s in labels if s not in ground]
        image = base64.b64encode(shrink((folder / "images" / row["image"]).read_bytes(), 768)).decode()
        result = vlm.describe(image, mode, "en")
        times.append(result.inference_ms)
        predicted = [h.what for h in result.scene.hazards if not not_ground(h.what)]
        detected, missed, alarms = match_hazards(ground + optional, predicted)
        caught += len(detected)
        total += len(ground)
        false_alarms += len(alarms)
        if not ground:
            clear += 1
            clear_warned += bool(alarms)
        if missed or alarms:
            print(f"  [{mode}] {row['image']}: missed={missed} false={alarms} said={predicted}")
    return caught, total, clear_warned, clear, false_alarms, statistics.median(times)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", choices=SETS, default="tuning")
    parser.add_argument("--modes", nargs="+", default=["surroundings"])
    args = parser.parse_args()
    ok, message, fix = vlm.check_model()
    if not ok:
        sys.exit(f"{message} {fix}")
    folder = SETS[args.set]
    with (folder / "labels.csv").open(newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("hazards_true") or "").strip().lower() != "n/a"]
    lines = [f"Set: {args.set}, {len(rows)} images, model {config.MODEL}", "",
             "| Mode | Ground hazards found | Clear scenes with a false ground warning | False ground warnings | Median latency |",
             "| --- | --- | --- | --- | --- |"]
    for mode in args.modes:
        caught, total, warned, clear, alarms, ms = score(rows, folder, mode)
        lines.append(f"| {mode} | {caught} of {total} | {warned} of {clear} | {alarms} | {ms:.0f} ms |")
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()

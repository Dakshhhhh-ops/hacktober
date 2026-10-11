"""Evaluate DrishtiAI on a folder of labelled images.

    python eval/run_eval.py

Uses the same drishti.vlm.describe() pipeline as the app. Writes eval/results.json
(every prediction next to its ground-truth label) and eval/results.md (a table for the
README). See eval/README.md for the label format and the matching rules.
"""
import argparse
import base64
import csv
import json
import re
import statistics
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from drishti import config, vlm  # noqa: E402

HAZARD_MATCH_RATIO = 0.75   # fuzzy threshold for a predicted hazard to match a label
TEXT_CORRECT_RATIO = 0.80   # similarity at or above this counts as "read correctly"


def normalise(text: str) -> str:
    """Lowercase, drop punctuation, collapse spaces."""
    return " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())


def _singular(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") else word


def phrases_match(label: str, predicted: str) -> bool:
    """A label matches a predicted phrase if one contains the other, or they are similar."""
    a = " ".join(_singular(w) for w in normalise(label).split())
    b = " ".join(_singular(w) for w in normalise(predicted).split())
    if not a or not b:
        return False
    return a in b or b in a or SequenceMatcher(None, a, b).ratio() >= HAZARD_MATCH_RATIO


def parse_hazard_labels(cell: str) -> list[list[str]]:
    """'stairs|steps;wet floor' -> [['stairs', 'steps'], ['wet floor']]"""
    return [[s.strip() for s in item.split("|") if s.strip()]
            for item in cell.split(";") if item.strip()]


def match_hazards(labels: list[list[str]], predicted: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (detected labels, missed labels, false-alarm predictions).

    Each prediction can satisfy at most one label and each label needs one prediction.
    """
    unused = list(predicted)
    detected, missed = [], []
    for synonyms in labels:
        hit = next((p for p in unused if any(phrases_match(s, p) for s in synonyms)), None)
        if hit is None:
            missed.append(synonyms[0])
        else:
            detected.append(synonyms[0])
            unused.remove(hit)
    return detected, missed, unused


def text_similarity(truth: str, predicted_lines: list[str]) -> float:
    """0-1 similarity between the labelled text and everything the model read."""
    return SequenceMatcher(None, normalise(truth), normalise(" ".join(predicted_lines))).ratio()


def percentile(values: list[float], p: float) -> float:
    """Nearest-rank percentile; with few samples p95 is simply the slowest or near it."""
    ordered = sorted(values)
    rank = max(1, round(p / 100 * len(ordered) + 0.5))
    return ordered[min(rank, len(ordered)) - 1]


def evaluate(rows: list[dict], images_dir: Path, describe=vlm.describe) -> list[dict]:
    """Run the pipeline on every labelled image. One result dict per image."""
    results = []
    for row in rows:
        name = row["image"].strip()
        path = images_dir / name
        hazard_cell = (row.get("hazards_true") or "").strip()
        # "n/a" marks an image that is only a reading test (for example rendered text).
        score_hazards = hazard_cell.lower() != "n/a"
        labels = parse_hazard_labels(hazard_cell) if score_hazards else []
        text_true = (row.get("text_true") or "").strip()
        item = {"image": name, "hazards_scored": score_hazards,
                "hazards_true": [s[0] for s in labels], "text_true": text_true,
                "hazards_predicted": [], "detected": [], "missed": [], "false_alarms": [],
                "failed": False, "error": "", "latencies_ms": []}
        results.append(item)
        if not path.exists():
            item.update(failed=True, error="image file not found")
            continue
        image_b64 = base64.b64encode(path.read_bytes()).decode()
        try:
            if score_hazards:
                scene = describe(image_b64, "surroundings", "en")
                item["latencies_ms"].append(scene.inference_ms)
                item["status"] = scene.status
                item["hazards_predicted"] = [h.what for h in scene.scene.hazards]
                item["summary"] = scene.scene.summary
                detected, missed, false_alarms = match_hazards(labels, item["hazards_predicted"])
                item.update(detected=detected, missed=missed, false_alarms=false_alarms)
            if text_true:
                read = describe(image_b64, "read", "en")
                item["latencies_ms"].append(read.inference_ms)
                item.setdefault("status", read.status)
                item["text_predicted"] = read.scene.text
                item["text_similarity"] = round(text_similarity(text_true, read.scene.text), 3)
        except vlm.VLMError as err:
            item.update(failed=True, error=str(err))
        print(f"  {name}: " + ("FAILED " + item["error"] if item["failed"] else
              f"missed={item['missed']} false_alarms={item['false_alarms']} "
              f"text_similarity={item.get('text_similarity', 'n/a')}"))
    return results


def summarise(results: list[dict]) -> dict:
    done = [r for r in results if not r["failed"]]
    detected = sum(len(r["detected"]) for r in done)
    missed = sum(len(r["missed"]) for r in done)
    false_alarms = sum(len(r["false_alarms"]) for r in done)
    predicted = sum(len(r["hazards_predicted"]) for r in done)
    scored = [r for r in done if r["hazards_scored"]]
    hazard_free = [r for r in scored if not r["hazards_true"]]
    texts = [r["text_similarity"] for r in done if "text_similarity" in r]
    latencies = [ms for r in done for ms in r["latencies_ms"]]
    return {
        "images": len(results),
        "images_scored_for_hazards": len(scored),
        "failed_inferences": len(results) - len(done),
        "fallbacks": sum(r.get("status") == "fallback" for r in done),
        "hazards_labelled": detected + missed,
        "hazards_detected": detected,
        "hazards_missed": missed,
        "hazard_recall": round(detected / (detected + missed), 3) if detected + missed else None,
        "hazards_predicted": predicted,
        "false_alarms": false_alarms,
        "false_alarms_per_image": round(false_alarms / len(scored), 2) if scored else None,
        # Share of the model's hazard reports that matched no labelled hazard.
        "false_alarm_rate": round(false_alarms / predicted, 3) if predicted else None,
        "hazard_free_images": len(hazard_free),
        "hazard_free_images_with_alarm": sum(bool(r["false_alarms"]) for r in hazard_free),
        "text_images": len(texts),
        "text_mean_similarity": round(statistics.mean(texts), 3) if texts else None,
        "text_read_correctly": sum(s >= TEXT_CORRECT_RATIO for s in texts),
        "inferences_timed": len(latencies),
        "latency_median_ms": round(statistics.median(latencies)) if latencies else None,
        "latency_p95_ms": round(percentile(latencies, 95)) if latencies else None,
    }


def _show(value, suffix="") -> str:
    return "n/a" if value is None else f"{value}{suffix}"


def to_markdown(summary: dict, results: list[dict], model: str) -> str:
    s = summary
    recall = "n/a" if s["hazard_recall"] is None else f"{s['hazard_recall']:.0%}"
    rate = "n/a" if s["false_alarm_rate"] is None else f"{s['false_alarm_rate']:.0%}"
    lines = [
        f"Model `{model}`, {s['images']} images, run {datetime.now():%Y-%m-%d %H:%M}.",
        "",
        f"**Missed hazards (false negatives): {s['hazards_missed']} of {s['hazards_labelled']} labelled hazards.**",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Images evaluated | {s['images']} ({s['images_scored_for_hazards']} scored for hazards, {s['text_images']} for reading) |",
        f"| Failed inferences | {s['failed_inferences']} |",
        f"| Plain-text fallbacks (no validated JSON) | {s['fallbacks']} |",
        f"| Hazard recall | {recall} ({s['hazards_detected']} of {s['hazards_labelled']}) |",
        f"| **Missed hazards** | **{s['hazards_missed']}** |",
        f"| False alarms | {s['false_alarms']} ({_show(s['false_alarms_per_image'])} per image) |",
        f"| False-alarm rate (false alarms / all hazards the model reported) | {rate} ({s['false_alarms']} of {s['hazards_predicted']}) |",
        f"| Hazard-free images that still got a warning | {s['hazard_free_images_with_alarm']} of {s['hazard_free_images']} |",
        f"| Text read correctly (similarity >= {TEXT_CORRECT_RATIO:.0%}) | {s['text_read_correctly']} of {s['text_images']} |",
        f"| Mean text similarity | {_show(s['text_mean_similarity'])} |",
        f"| Median model latency | {_show(s['latency_median_ms'], ' ms')} |",
        f"| p95 model latency | {_show(s['latency_p95_ms'], ' ms')} ({s['inferences_timed']} inferences) |",
        "",
    ]
    missed = [(r["image"], m) for r in results if not r["failed"] for m in r["missed"]]
    if missed:
        lines += ["Missed hazards, by image:", ""]
        lines += [f"- `{image}`: {hazard}" for image, hazard in missed]
        lines.append("")
    if s["images"] < 30:
        lines += [f"With only {s['images']} images these numbers describe this image set. "
                  "They are not a statistically meaningful estimate of real-world performance.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--images", type=Path, default=ROOT / "eval" / "images")
    parser.add_argument("--labels", type=Path, default=ROOT / "eval" / "labels.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "eval")
    args = parser.parse_args()

    with args.labels.open(newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("image") or "").strip()]
    if not rows:
        sys.exit(f"No rows in {args.labels}. Add images to {args.images} and label them first.")
    ok, message, fix = vlm.check_model()
    if not ok:
        sys.exit(f"{message} {fix}")

    print(f"Evaluating {len(rows)} images with {config.MODEL} ...")
    results = evaluate(rows, args.images)
    summary = summarise(results)
    (args.out / "results.json").write_text(
        json.dumps({"model": config.MODEL, "summary": summary, "images": results}, indent=2,
                   ensure_ascii=False), encoding="utf-8")
    markdown = to_markdown(summary, results, config.MODEL)
    (args.out / "results.md").write_text(markdown, encoding="utf-8")
    print("\n" + markdown)
    print(f"Saved {args.out / 'results.json'} and {args.out / 'results.md'}")


if __name__ == "__main__":
    main()

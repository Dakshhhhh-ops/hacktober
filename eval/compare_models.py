"""Put the evaluation results of several models side by side.

    python eval/compare_models.py

Reads eval/compare/<model>/<set>/results.json, as written by

    OLLAMA_MODEL=<model> python eval/run_eval.py --images ... --labels ... --out eval/compare/<model>/<set>

and writes eval/compare/README.md.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent / "compare"
SETS = ("tuning", "heldout", "currency")
NOTES = """Notes:

- The `qwen3-vl:2b-instruct` rows were run after the JSON length limits were added
  (see the main README, section 14), as was every currency row. The tuning and held-out
  rows of the other two models were run before them, on
  14 October 2026, and have not been tuned for: their prompts are the 2B model's.
- `qwen3-vl:4b-instruct` almost never reports a hazard with these prompts, although it
  reads text and money well.
- `gemma3:4b` ran fully on the GPU but took about 30 s per image.
- Money mode was added after the gemma run, so gemma has no currency row."""


def _pct(part, whole) -> str:
    return f"{part / whole:.0%} ({part}/{whole})" if whole else "n/a"


def row(model: str, name: str, s: dict) -> str:
    cells = [f"`{model}`", name]
    if s["hazards_labelled"]:
        cells += [_pct(s["hazards_detected"], s["hazards_labelled"]), str(s["hazards_missed"]),
                  f"{s['hazard_free_images_with_alarm']}/{s['hazard_free_images']}"]
    else:
        cells += ["", "", ""]
    cells.append(f"{s['text_read_correctly']}/{s['text_images']}" if s["text_images"] else "")
    cells.append(f"{s['money_correct']}/{s['money_images']} ({s['money_wrong_value']} wrong)"
                 if s.get("money_images") else "")
    cells += [str(s["fallbacks"]), f"{s['latency_median_ms']} ms"]
    return "| " + " | ".join(cells) + " |"


def main() -> None:
    lines = [
        "# Model comparison",
        "",
        "Each model was run on each image set with the same prompts and code. The prompts were",
        "written against the tuning set, so the held-out numbers are the fairer estimate. Latency",
        "is the median time inside the model on an RTX 4050 Laptop GPU (6 GB), model already loaded.",
        "",
        "| Model | Set | Hazard recall | Missed | Clear scenes with a false warning | Text read | Money right | JSON fallbacks | Median latency |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for folder in sorted(p for p in HERE.iterdir() if p.is_dir()):
        for name in SETS:
            path = folder / name / "results.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                lines.append(row(data["model"], name, data["summary"]))
    lines += ["", NOTES]
    (HERE / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

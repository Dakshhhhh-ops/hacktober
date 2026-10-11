"""Append one CSV row per vision-model inference attempt. Images are never logged."""
import csv
from datetime import datetime

from . import config

FIELDS = [
    "timestamp", "request_id", "mode", "model", "lang", "attempt",
    "inference_ms", "retry_count", "parse_outcome", "request_outcome",
]


def log_attempts(request_id: str, mode: str, lang: str, attempts: list[dict], request_outcome: str) -> None:
    """attempts: [{"inference_ms": int, "parse_outcome": str}, ...] in the order they ran."""
    path = config.LATENCY_CSV
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if is_new:
                writer.writeheader()
            now = datetime.now().isoformat(timespec="seconds")
            for number, attempt in enumerate(attempts, start=1):
                writer.writerow({
                    "timestamp": now, "request_id": request_id, "mode": mode,
                    "model": config.MODEL, "lang": lang, "attempt": number,
                    "inference_ms": attempt["inference_ms"], "retry_count": len(attempts) - 1,
                    "parse_outcome": attempt["parse_outcome"], "request_outcome": request_outcome,
                })
    except OSError as err:
        # Logging must never take the app down (file open in Excel, disk full, ...).
        print(f"[latency_log] could not write {path}: {err}")

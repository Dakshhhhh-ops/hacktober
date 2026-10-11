"""Check the REAL local model end to end. Needs Ollama running with the model pulled.

    python tests/integration_check.py

Not part of the unit tests: it is slow and its result depends on the model. It sends one
rendered sign through the shared pipeline in Read and Surroundings modes and reports what
actually came back, including latency.
"""
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from drishti import config, tts, vlm  # noqa: E402

IMAGE = ROOT / "eval" / "images" / "synthetic_exit_sign.png"


def main() -> int:
    ok, message, fix = vlm.check_model()
    print(f"model: {message} {fix}".rstrip())
    if not ok:
        return 1
    image = base64.b64encode(IMAGE.read_bytes()).decode()
    failures = 0

    for mode in ("read", "surroundings"):
        try:
            result = vlm.describe(image, mode, "en")
        except vlm.VLMError as err:
            print(f"{mode}: FAILED - {err} {err.fix}")
            failures += 1
            continue
        print(f"{mode}: status={result.status} retries={result.retries} "
              f"latency={result.inference_ms} ms")
        print(f"  hazards={[h.what for h in result.scene.hazards]} text={result.scene.text} "
              f"summary={result.scene.summary!r}")
        if result.status != "ok":
            print("  NOT OK: the model did not return valid JSON")
            failures += 1
        if mode == "read" and "exit" not in " ".join(result.scene.text).lower():
            print("  NOT OK: the sign says EXIT and the model did not read it")
            failures += 1

    for lang in ("en", "hi"):
        engine = tts.engine(lang)
        print(f"voice {lang}: {engine or 'none installed'}")
        failures += engine is None

    print("PASS" if failures == 0 else f"{failures} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    print(f"Checking {config.MODEL} at {config.OLLAMA_URL}")
    sys.exit(main())

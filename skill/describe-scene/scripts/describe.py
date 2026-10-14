"""Describe one image with DrishtiAI's local vision pipeline and print JSON.

    python skill/describe-scene/scripts/describe.py photo.jpg
    python skill/describe-scene/scripts/describe.py label.png --mode read
    python skill/describe-scene/scripts/describe.py desk.jpg --mode find --target "keys" --lang hi

Exit code 0 with {"status": "ok" | "fallback", ...} when the model answered.
Exit code 1 with {"status": "error", ...} when it did not. An error means the image was
NOT inspected.
"""
import argparse
import base64
import json
import sys
from pathlib import Path

# The skill lives inside the DrishtiAI repository and reuses its pipeline.
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from drishti import config, vlm  # noqa: E402

IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")  # JPEG, PNG


def fail(message: str, fix: str = "") -> None:
    print(json.dumps({"status": "error", "model": config.MODEL,
                      "error": {"message": message, "fix": fix}}, indent=2))
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", type=Path, help="path to a JPEG or PNG file")
    parser.add_argument("--mode", choices=["surroundings", "read", "find", "money"], default="surroundings")
    parser.add_argument("--lang", choices=["en", "hi"], default="en")
    parser.add_argument("--target", default="", help="what to look for (find mode)")
    args = parser.parse_args()

    if not args.image.is_file():
        fail(f"No such file: {args.image}")
    data = args.image.read_bytes()
    if len(data) > config.MAX_IMAGE_BYTES:
        fail(f"The image is larger than {config.MAX_IMAGE_BYTES // (1024 * 1024)} MB.",
             "Resize it first.")
    if not data.startswith(IMAGE_SIGNATURES):
        fail("The file is not a JPEG or PNG image.")
    if args.mode == "find" and not args.target.strip():
        fail("Find mode needs --target.", 'Example: --mode find --target "water bottle"')

    try:
        result = vlm.describe(base64.b64encode(data).decode(), args.mode, args.lang, args.target)
    except vlm.VLMError as err:
        fail(str(err), err.fix)

    output = {
        "status": result.status,
        "model": result.model,
        "mode": args.mode,
        "scene": result.scene.model_dump(),
        "inference_ms": result.inference_ms,
        "retries": result.retries,
    }
    if result.find_result is not None:
        output["find_result"] = result.find_result.model_dump()
    if args.mode == "money":
        output["money"] = [item.model_dump() for item in result.money]
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

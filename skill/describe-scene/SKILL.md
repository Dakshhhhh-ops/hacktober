---
name: describe-scene
description: Describes a photo for a blind or low-vision person using a local, offline, open-weight vision-language model (via Ollama). Returns strict JSON listing physical hazards first (what, direction, rough distance), then objects, visible text and a one-line summary. Use when the user asks what is in an image, whether a path or room has obstacles, to read text on a label, sign or medicine strip, or to find an object in a photo, and the image must not leave the machine.
license: MIT
compatibility: Requires Python 3.11+, Ollama running locally with a vision model pulled (default qwen3-vl:2b-instruct), and the DrishtiAI repository this skill ships in. No network access is needed at run time.
metadata:
  author: Dakshhhhh-ops
  version: "1.0"
---

# Describe Scene

Turn one image into a hazard-first description, using the same pipeline as the DrishtiAI
app. The image is sent only to the model running on this machine.

## How to run it

```
python scripts/describe.py <image> [--mode surroundings|read|find] [--target "<object>"] [--lang en|hi]
```

Run it from this skill's folder inside the DrishtiAI repository, with the repository's
Python environment (`pip install -r requirements.txt`). The image must be a JPEG or PNG.

| Mode | Use it when | Read the answer from |
| --- | --- | --- |
| `surroundings` (default) | The user wants to know what is around them or whether the way is clear. | `scene.hazards`, then `scene.summary` |
| `read` | The user wants text read: a sign, a label, a medicine strip. | `scene.text` |
| `find` | The user is looking for one object. Pass it with `--target`. | `find_result` |

The model is chosen with the `OLLAMA_MODEL` environment variable or the repository's
`.env` file.

## Output

```json
{
  "status": "ok",
  "model": "qwen3-vl:2b-instruct",
  "mode": "surroundings",
  "scene": {
    "hazards": [{"what": "stairs", "where": "ahead", "distance": "near"}],
    "objects": [{"what": "chair", "where": "left"}],
    "text": ["EXIT"],
    "summary": "A chair is on the left, with stairs ahead."
  },
  "inference_ms": 2300,
  "retries": 0
}
```

- `where` for a hazard is one of `left`, `right`, `ahead`, `below`; `distance` is `near`,
  `mid` or `far`. Both are rough visual judgements from a single camera, not measurements.
- In find mode there is also `"find_result": {"status": "found" | "not_found" | "uncertain", "where": "..."}`.

## How to report the result to the user

1. Say the hazards first, nearest first: "Careful: stairs ahead, near."
2. Then one line: the summary, the text that was read, or the find result.
3. Do not list every object unless the user asks.
4. If there are no hazards, describe the scene. Never say the scene is safe: the model can
   miss things.

## When it does not work

Check `status` before saying anything about the image.

- `"status": "error"` (exit code 1): the image was **not** inspected. Tell the user so and
  pass on `error.fix`, for example "Start Ollama" or "Run: ollama pull qwen3-vl:2b-instruct". Do
  not describe the image from its file name or from guesswork.
- `"status": "fallback"`: the model's JSON was invalid twice, so `scene.summary` holds a
  plain-text description and `hazards` is empty because hazards could not be checked, not
  because there are none. Say that the description is rough.
- `find_result.status` of `uncertain` means exactly that. Do not turn it into yes or no.

## Limits

- Small vision models invent and miss things. Treat medicine names, doses and other
  safety-critical text as unverified and suggest a second check.
- Text that is blurred, curved or small is often misread.
- This is an aid, not a replacement for a cane, a guide dog or a human guide.

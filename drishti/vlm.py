"""Send one image to the vision model and get a validated Scene back.

This is the single inference pipeline. The web app, the evaluation script and the
Agent Skill all call describe().
"""
import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field

from pydantic import ValidationError

from . import config
from .latency_log import log_attempts
from .schema import FindResult, FindScene, Scene


class VLMError(RuntimeError):
    """The vision model could not be reached or gave nothing usable."""

    def __init__(self, message: str, fix: str = ""):
        super().__init__(message)
        self.fix = fix


@dataclass
class Result:
    scene: Scene
    find_result: FindResult | None
    status: str  # "ok" (validated JSON) or "fallback" (plain-text summary only)
    retries: int
    inference_ms: int
    request_id: str
    model: str
    attempts: list[dict] = field(default_factory=list)


def _prompt(name: str) -> str:
    return (config.PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8").strip()


def build_messages(image_b64: str, mode: str, lang: str, target: str = "") -> list[dict]:
    user = "\n\n".join([
        _prompt(f"mode_{mode}").replace("{target}", target.strip() or "unclear"),
        _prompt(f"lang_{lang}"),
        _prompt("schema_find" if mode == "find" else "schema"),
    ])
    return [
        {"role": "system", "content": _prompt("describe_scene")},
        {"role": "user", "content": user, "images": [image_b64]},
    ]


def _post_ollama(payload: dict) -> str:
    """POST to Ollama's chat endpoint and return the reply text."""
    request = urllib.request.Request(
        config.OLLAMA_URL + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=config.VLM_TIMEOUT_S) as response:
            return json.loads(response.read())["message"]["content"]
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:200]
        if err.code == 404:
            raise VLMError(f"The model '{payload['model']}' is not downloaded.",
                           fix=f"Run: ollama pull {payload['model']}") from err
        raise VLMError(f"Ollama returned an error ({err.code}): {detail}",
                       fix="Check the Ollama window or run: ollama ps") from err
    except (urllib.error.URLError, TimeoutError, ConnectionError) as err:
        raise VLMError(f"Could not reach Ollama at {config.OLLAMA_URL}.",
                       fix="Start Ollama (open the Ollama app, or run: ollama serve).") from err


def parse_scene(text: str, mode: str = "surroundings") -> Scene:
    """Validate the model's reply. Tolerates code fences or stray text around the JSON."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the reply")
    schema = FindScene if mode == "find" else Scene
    return schema.model_validate_json(text[start:end + 1])


def _parse_outcome(error: Exception) -> str:
    return "schema_error" if isinstance(error, ValidationError) else "invalid_json"


def describe(image_b64: str, mode: str = "surroundings", lang: str = "en", target: str = "",
             *, post=_post_ollama, log: bool = True) -> Result:
    """Describe one base64-encoded image.

    Asks for strict JSON. If the reply does not validate, asks once more with the error,
    then falls back to a plain-text summary. Hazards are never invented to fill a gap:
    a fallback Scene has an empty hazard list and status "fallback".
    """
    request_id = uuid.uuid4().hex[:12]
    schema = FindScene if mode == "find" else Scene
    messages = build_messages(image_b64, mode, lang, target)
    payload = {
        "model": config.MODEL,
        "messages": messages,
        "stream": False,
        "format": schema.model_json_schema(),
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_predict": config.MAX_TOKENS},
    }
    attempts: list[dict] = []

    def timed_post(request_payload: dict) -> str:
        started = time.perf_counter()
        try:
            return post(request_payload)
        finally:
            attempts.append({
                "inference_ms": round((time.perf_counter() - started) * 1000),
                "parse_outcome": "error",  # overwritten once the reply has been checked
            })

    def finish(outcome: str) -> None:
        if log:
            log_attempts(request_id, mode, lang, attempts, outcome)

    scene, status = None, "ok"
    try:
        reply = timed_post(payload)
        try:
            scene = parse_scene(reply, mode)
            attempts[-1]["parse_outcome"] = "valid"
        except (ValueError, ValidationError) as first_error:
            attempts[-1]["parse_outcome"] = _parse_outcome(first_error)
            correction = dict(payload, messages=messages + [
                {"role": "assistant", "content": reply},
                {"role": "user", "content":
                    f"That was not valid JSON for the schema ({str(first_error)[:300]}). "
                    "Respond again with ONLY the JSON object."},
            ])
            reply = timed_post(correction)
            try:
                scene = parse_scene(reply, mode)
                attempts[-1]["parse_outcome"] = "valid"
            except (ValueError, ValidationError) as second_error:
                attempts[-1]["parse_outcome"] = _parse_outcome(second_error)
                status = "fallback"
                plain = dict(payload, messages=[{
                    "role": "user",
                    "content": _prompt("fallback") + "\n" + _prompt(f"lang_{lang}"),
                    "images": [image_b64],
                }])
                del plain["format"]
                summary = " ".join(timed_post(plain).split())[:300]
                if not summary:
                    raise VLMError("The vision model returned an empty reply.",
                                   fix="Try again, or try a different model.")
                attempts[-1]["parse_outcome"] = "plain_text"
                scene = Scene.from_summary(summary)
    except VLMError:
        finish("error")
        raise

    finish(status)
    find_result = scene.find_result if isinstance(scene, FindScene) else None
    return Result(
        scene=Scene(hazards=scene.hazards, objects=scene.objects, text=scene.text,
                    summary=scene.summary),
        find_result=find_result,
        status=status,
        retries=len(attempts) - 1,
        inference_ms=sum(a["inference_ms"] for a in attempts),
        request_id=request_id,
        model=config.MODEL,
        attempts=attempts,
    )


def check_model() -> tuple[bool, str, str]:
    """Is Ollama running with the configured model? Returns (ok, message, fix)."""
    try:
        with urllib.request.urlopen(config.OLLAMA_URL + "/api/tags", timeout=3) as response:
            names = [m["name"] for m in json.loads(response.read()).get("models", [])]
    except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError):
        return (False, f"Ollama is not running at {config.OLLAMA_URL}.",
                "Start Ollama (open the Ollama app, or run: ollama serve).")
    wanted = config.MODEL if ":" in config.MODEL else config.MODEL + ":latest"
    if wanted not in names:
        return (False, f"The model '{config.MODEL}' is not downloaded.",
                f"Run: ollama pull {config.MODEL}")
    return True, f"{config.MODEL} is ready.", ""

"""FastAPI app: serves the web page and the endpoints it calls.

Run with:  python -m drishti
"""
import base64
import binascii
import mimetypes
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, tts, vlm
from .schema import DescribeResponse, ErrorInfo, Lang, Mode, Speech
from .speech import RepeatFilter, build_speech

# Windows sometimes maps .js to text/plain, which browsers refuse for module scripts.
mimetypes.add_type("text/javascript", ".js")

app = FastAPI(title="DrishtiAI")
repeats = RepeatFilter(config.REPEAT_SUPPRESS_S)

_IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")  # JPEG, PNG


class DescribeRequest(BaseModel):
    image: str  # base64 JPEG or PNG, with or without a "data:image/...;base64," prefix
    mode: Mode = "surroundings"
    lang: Lang = "en"
    target: str = Field(default="", max_length=config.MAX_TARGET_CHARS)
    auto: bool = False  # true when the page sent the frame by itself, not on a key press


class SpeakRequest(BaseModel):
    text: str = Field(max_length=2000)
    lang: Lang = "en"


def _check_image(image_b64: str) -> str | None:
    """Return a problem description, or None if the image is acceptable."""
    if len(image_b64) * 3 / 4 > config.MAX_IMAGE_BYTES:
        return f"The image is larger than {config.MAX_IMAGE_BYTES // (1024 * 1024)} MB."
    try:
        head = base64.b64decode(image_b64[:24], validate=True)
    except (binascii.Error, ValueError):
        return "The image is not valid base64."
    if not head.startswith(_IMAGE_SIGNATURES):
        return "The image must be a JPEG or PNG."
    return None


def _error(request: DescribeRequest, status_code: int, message: str, fix: str = "",
           started: float | None = None) -> JSONResponse:
    body = DescribeResponse(
        request_id="", status="error", mode=request.mode, lang=request.lang, model=config.MODEL,
        total_ms=round((time.perf_counter() - started) * 1000) if started else 0,
        error=ErrorInfo(message=message, fix=fix),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


@app.get("/api/health")
def health():
    model_ok, message, fix = vlm.check_model()
    return {
        "model": config.MODEL,
        "model_ok": model_ok,
        "model_message": message,
        "model_fix": fix,
        "tts": {lang: tts.engine(lang) for lang in ("en", "hi")},
        "change_threshold": config.CHANGE_THRESHOLD,
        "min_interval_s": config.MIN_INTERVAL_S,
    }


@app.post("/api/describe", response_model=DescribeResponse)
def describe(request: DescribeRequest):
    started = time.perf_counter()
    image = request.image.split(",", 1)[-1].strip()
    problem = _check_image(image)
    if problem:
        return _error(request, 400, problem, "Send a camera frame as a JPEG.", started)
    if request.mode == "find" and not request.target.strip():
        return _error(request, 400, "Find mode needs the name of an object.",
                      "Type what you are looking for, then press Describe.", started)

    try:
        result = vlm.describe(image, request.mode, request.lang, request.target)
    except vlm.VLMError as err:
        return _error(request, 503, str(err), err.fix, started)

    hazards, rest = build_speech(result.scene, request.mode, request.lang, request.target,
                                 result.find_result, fallback=result.status == "fallback")
    if request.auto:
        # Automatic frames only speak what has not been said recently.
        hazards, rest = repeats.fresh(hazards), repeats.fresh(rest)
    else:
        repeats.remember(hazards + rest)

    return DescribeResponse(
        request_id=result.request_id, status=result.status, mode=request.mode, lang=request.lang,
        model=result.model, scene=result.scene, find_result=result.find_result,
        speech=Speech(hazards=hazards, rest=rest), retries=result.retries,
        inference_ms=result.inference_ms,
        total_ms=round((time.perf_counter() - started) * 1000),
    )


@app.post("/api/speak")
def speak(request: SpeakRequest):
    """Synthesise speech offline. 503 means no local voice; the page then says so."""
    try:
        audio = tts.synthesize(request.text, request.lang) if request.text.strip() else None
    except Exception as err:  # a TTS failure must not take the app down
        print(f"[tts] synthesis failed: {err}")
        audio = None
    if audio is None:
        return JSONResponse(status_code=503, content={
            "message": f"No offline voice is available for '{request.lang}'.",
            "fix": "Run: python -m piper.download_voices "
                   f"{config.PIPER_VOICES[request.lang]} --download-dir voices",
        })
    return Response(content=audio, media_type="audio/wav")


app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")

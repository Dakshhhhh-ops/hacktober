"""FastAPI app: serves the web page and the endpoints it calls.

Run with:  python -m drishti
"""
import base64
import binascii
import mimetypes
import secrets
import threading
import time

from fastapi import Body, FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, detector, tts, vlm, voice
from .schema import (DescribeResponse, ErrorInfo, FindResult, Hazard, Lang, Mode, Money, Scene,
                     Speech)
from .speech import (RepeatFilter, build_speech, hazard_cards, hazard_sentence, locate_sentence,
                     object_names)

# Windows sometimes maps .js to text/plain, which browsers refuse for module scripts.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/manifest+json", ".webmanifest")

app = FastAPI(title="DrishtiAI")
repeats = RepeatFilter(config.REPEAT_SUPPRESS_S)

_IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")  # JPEG, PNG
KEY_COOKIE = "drishti_key"


def _key_matches(given: str | None) -> bool:
    return bool(given) and secrets.compare_digest(given.encode(), config.ACCESS_KEY.encode())


@app.middleware("http")
async def require_access_key(request: Request, call_next):
    """In phone mode, only a device that opened the QR code's link may use the app.

    The link carries ?key=...; the page is then reloaded without it and the key is kept
    in a cookie the page's scripts cannot read.
    """
    if not config.ACCESS_KEY or _key_matches(request.cookies.get(KEY_COOKIE)):
        return await call_next(request)
    if _key_matches(request.query_params.get("key")):
        response = RedirectResponse(request.url.path, status_code=303)
        response.set_cookie(KEY_COOKIE, config.ACCESS_KEY, max_age=30 * 24 * 3600,
                            httponly=True, secure=True, samesite="strict")
        return response
    return PlainTextResponse(
        "DrishtiAI: this device does not have the access key. Scan the QR code shown on the "
        "computer running DrishtiAI, or open the full link it prints.", status_code=403)


class DescribeRequest(BaseModel):
    image: str  # base64 JPEG or PNG, with or without a "data:image/...;base64," prefix
    mode: Mode = "surroundings"
    lang: Lang = "en"
    target: str = Field(default="", max_length=config.MAX_TARGET_CHARS)
    auto: bool = False  # true when the page sent the frame by itself, not on a key press
    blurry: bool = False  # the page measured the frame as blurred (web/quality.js)
    # Walk mode's check for the ground: only hazards the object detector cannot see
    # (holes, drains, steps, water) are returned, and nothing else is spoken.
    walk: bool = False


class RenderRequest(BaseModel):
    """A scene the model already produced, to be worded again in another language."""
    scene: Scene
    mode: Mode = "surroundings"
    lang: Lang = "en"
    target: str = Field(default="", max_length=config.MAX_TARGET_CHARS)
    find_result: FindResult | None = None
    money: list[Money] = []
    fallback: bool = False
    blurry: bool = False


class DetectRequest(BaseModel):
    image: str  # base64 JPEG or PNG, as for /api/describe
    lang: Lang = "en"


class LocateRequest(BaseModel):
    image: str  # base64 JPEG or PNG, as for /api/describe
    target: str = Field(max_length=config.MAX_TARGET_CHARS)
    lang: Lang = "en"


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
        "voice": {lang: voice.available(lang) for lang in ("en", "hi")},
        "voice_engine": voice.engine("en"),
        "detector": detector.available(),
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
    if request.walk:
        # People, vehicles and animals come from the detector several times a second.
        ground = [h for h in result.scene.hazards if not detector.handles(h.what)]
        result.scene = result.scene.model_copy(update={"hazards": ground, "objects": [],
                                                       "text": [], "summary": ""})

    hazards, rest = build_speech(result.scene, request.mode, request.lang, request.target,
                                 result.find_result, fallback=result.status == "fallback",
                                 money=result.money, blurry=request.blurry)
    if request.auto:
        # Automatic frames only speak what has not been said recently.
        hazards, rest = repeats.fresh(hazards), repeats.fresh(rest)
    else:
        repeats.remember(hazards + rest)

    return DescribeResponse(
        request_id=result.request_id, status=result.status, mode=request.mode, lang=request.lang,
        model=result.model, scene=result.scene, find_result=result.find_result, money=result.money,
        speech=Speech(hazards=hazards, rest=rest),
        hazards=[c for c in hazard_cards(result.scene, request.lang) if c["sentence"] in hazards],
        objects=object_names(result.scene, request.lang), target=request.target.strip(),
        blurry=request.blurry, retries=result.retries, inference_ms=result.inference_ms,
        total_ms=round((time.perf_counter() - started) * 1000),
    )


@app.post("/api/detect")
def detect(request: DetectRequest):
    """Walk mode: a fast check for people, vehicles and animals that are close or ahead.

    Every current warning is returned. The page decides what to say, and does not repeat
    a warning it has actually played in the last few seconds: if the server marked it as
    said and the page was then cut off mid-sentence, the warning would be lost. This uses
    the object detector alone (tens of milliseconds); the vision-language model is not called.
    """
    started = time.perf_counter()
    image = request.image.split(",", 1)[-1].strip()
    problem = _check_image(image)
    if problem:
        return JSONResponse(status_code=400, content={"message": problem})
    if not detector.available():
        return JSONResponse(status_code=503, content={
            "message": "The object detector is not installed, so walk mode is unavailable.",
            "fix": "Download yolox_nano.onnx into models/yolox (see the README)."})
    try:
        frame = base64.b64decode(image, validate=True)
    except (binascii.Error, ValueError):
        return JSONResponse(status_code=400, content={"message": "The image is not valid base64."})
    found = detector.detect(frame)
    warnings = detector.walk_warnings(found)
    sentences = [hazard_sentence(h, request.lang) for h in warnings]
    return {
        "lang": request.lang,
        "speech": {"hazards": sentences, "rest": []},
        "hazards": [{"sentence": hazard_sentence(h, request.lang), "what": h.what,
                     "where": h.where, "distance": h.distance} for h in warnings],
        "objects": [{"label": d.label, "score": d.score, "box": d.box} for d in found],
        "detect_ms": round((time.perf_counter() - started) * 1000),
    }


def _object_name(target: str) -> str:
    """'my water bottle' -> 'water bottle', for saying it back."""
    words = target.split()
    while len(words) > 1 and words[0].lower() in ("my", "the", "a", "an", "mera", "meri"):
        words = words[1:]
    return " ".join(words)


def _spoken_name(target: str, matched: str, lang: str) -> str:
    """In English, the person's own words ("water bottle"); in Hindi, the matched object's
    last word, so a "laptop bag" is a बैग and not a लैपटॉप."""
    return _object_name(target) if lang == "en" else matched.split()[-1]


@app.post("/api/locate")
def locate(request: LocateRequest):
    """Live Find: where is the thing being looked for, in this frame? Tens of milliseconds.

    "known" is false when the object detector does not know this kind of thing; the page
    then asks the vision-language model instead.
    """
    started = time.perf_counter()
    match = detector.find_match(request.target)
    if match is None or not detector.available():
        return {"known": False, "found": False}
    image = request.image.split(",", 1)[-1].strip()
    problem = _check_image(image)
    if problem:
        return JSONResponse(status_code=400, content={"message": problem})
    try:
        frame = base64.b64decode(image, validate=True)
    except (binascii.Error, ValueError):
        return JSONResponse(status_code=400, content={"message": "The image is not valid base64."})
    name, labels = match
    best = detector.locate(detector.detect(frame), labels)
    answer = {"known": True, "found": best is not None,
              "detect_ms": round((time.perf_counter() - started) * 1000)}
    if best is not None:
        answer.update(where=best.where, distance=best.distance, box=best.box, score=best.score,
                      sentence=locate_sentence(_spoken_name(request.target, name, request.lang),
                                               best.where, best.distance, request.lang))
    return answer


def _warm_walk_voices() -> None:
    """Synthesise the walk-mode warnings ahead of time, so the first one is not slow."""
    for lang in ("en", "hi"):
        if tts.engine(lang) is None:
            continue
        for what in sorted(set(detector.HAZARD_NAMES.values())):
            for where, distance in (("left", "near"), ("ahead", "near"), ("right", "near"),
                                    ("ahead", "mid")):
                hazard = Hazard(what=what, where=where, distance=distance)
                tts.synthesize(hazard_sentence(hazard, lang), lang)


@app.on_event("startup")
def _start_warming() -> None:
    if detector.available():
        threading.Thread(target=_warm_walk_voices, daemon=True).start()


@app.post("/api/render", response_model=DescribeResponse)
def render(request: RenderRequest):
    """Word an existing scene again, for example after switching language. No model call."""
    hazards, rest = build_speech(request.scene, request.mode, request.lang, request.target,
                                 request.find_result, fallback=request.fallback,
                                 money=request.money, blurry=request.blurry)
    repeats.remember(hazards + rest)
    return DescribeResponse(
        request_id="", status="fallback" if request.fallback else "ok", mode=request.mode,
        lang=request.lang, model=config.MODEL, scene=request.scene,
        find_result=request.find_result, money=request.money,
        speech=Speech(hazards=hazards, rest=rest),
        hazards=hazard_cards(request.scene, request.lang),
        objects=object_names(request.scene, request.lang), target=request.target.strip(),
        blurry=request.blurry,
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


@app.post("/api/listen")
def listen(audio: bytes = Body(media_type="application/octet-stream"), lang: Lang = "en"):
    """Recognise one spoken command. The body is raw 16 kHz, 16-bit mono audio."""
    limit = voice.SAMPLE_RATE * 2 * voice.MAX_SECONDS
    if len(audio) < voice.SAMPLE_RATE * 2 // 5 or len(audio) > limit or len(audio) % 2:
        return JSONResponse(status_code=400, content={
            "message": f"Send between 0.2 and {voice.MAX_SECONDS} seconds of 16 kHz 16-bit mono audio."})
    if not voice.available(lang):
        return JSONResponse(status_code=503, content={
            "message": f"No offline speech model is installed for '{lang}'.",
            "fix": "Download a speech model into the models folder (see the README).",
        })
    return voice.recognise(audio, lang)


app.mount("/", StaticFiles(directory=config.WEB_DIR, html=True), name="web")

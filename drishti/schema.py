"""The JSON the vision model must return, and the envelope the API sends to the page."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

Where = Literal["left", "right", "ahead", "below"]
Distance = Literal["near", "mid", "far"]
Mode = Literal["surroundings", "read", "find", "money"]
Lang = Literal["en", "hi"]


class _Strict(BaseModel):
    # Strict: a number where a string is expected is an error, not silently converted.
    model_config = ConfigDict(strict=True)


class Hazard(_Strict):
    what: str
    where: Where
    distance: Distance

    @field_validator("where", "distance", mode="before")
    @classmethod
    def _tidy(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class SceneObject(_Strict):
    what: str
    where: str


class Scene(_Strict):
    hazards: list[Hazard]
    objects: list[SceneObject]
    text: list[str]
    summary: str

    @classmethod
    def from_summary(cls, summary: str) -> "Scene":
        """A scene with only a plain-text summary, used when the model's JSON was unusable."""
        return cls(hazards=[], objects=[], text=[], summary=summary)


class FindResult(_Strict):
    """Find mode's explicit answer. `where` is only set when the object is found."""
    status: Literal["found", "not_found", "uncertain"]
    where: str = ""


class FindScene(Scene):
    """What the model returns in Find mode: the common schema plus find_result."""
    find_result: FindResult


class Money(_Strict):
    """One Indian note or coin. Only values that are issued can be returned."""
    value: Literal[1, 2, 5, 10, 20, 50, 100, 200, 500, 2000]
    kind: Literal["note", "coin"]


class MoneyScene(Scene):
    """What the model returns in Money mode: the common schema plus the money seen."""
    money: list[Money]


class ErrorInfo(BaseModel):
    message: str
    fix: str = ""


class Speech(BaseModel):
    hazards: list[str] = []
    rest: list[str] = []


class HazardCard(BaseModel):
    """One warning, in the output language, for the page to draw."""
    sentence: str        # what is spoken, e.g. "Careful: stairs ahead, near."
    what: str            # "stairs" / "सीढ़ियाँ"
    where: Where
    distance: Distance


class DescribeResponse(BaseModel):
    request_id: str
    # "ok": validated JSON. "fallback": plain-text summary only. "error": nothing usable.
    status: Literal["ok", "fallback", "error"]
    mode: Mode
    lang: Lang
    model: str
    scene: Scene | None = None
    find_result: FindResult | None = None
    money: list[Money] = []  # Money mode: each note or coin seen
    speech: Speech = Speech()
    hazards: list[HazardCard] = []   # the warnings in speech.hazards, with their parts
    objects: list[str] = []          # names of things seen, in the output language
    target: str = ""
    blurry: bool = False   # the page said the frame was blurred
    retries: int = 0
    inference_ms: int = 0  # time spent inside the vision model, all attempts
    total_ms: int = 0      # whole request on the server; excludes speech synthesis and playback
    error: ErrorInfo | None = None

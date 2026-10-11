"""Turn a Scene into the sentences to speak. Hazards always come first.

This layer decides what is said; it never adds anything the model did not report, and
it never says a scene is safe.
"""
import time

from . import hindi
from .schema import FindResult, Hazard, Scene

MAX_OBJECTS_SPOKEN = 4

MAX_SUMMARY_WORDS = 25  # a long summary must not delay the next warning

WHERE = {
    "en": {"left": "on the left", "right": "on the right", "ahead": "ahead", "below": "below"},
    "hi": {"left": "बाईं ओर", "right": "दाईं ओर", "ahead": "सामने", "below": "नीचे"},
}
DISTANCE = {
    "en": {"near": "near", "mid": "mid distance", "far": "far"},
    "hi": {"near": "पास", "mid": "थोड़ी दूर", "far": "दूर"},
}
PHRASES = {
    "en": {
        "hazard": "Careful: {what} {where}, {distance}.",
        "found": "Found {target}: {where}.",
        "found_no_place": "Found {target}.",
        "not_found": "I cannot see {target}.",
        "uncertain": "I am not sure whether {target} is here.",
        "no_text": "No readable text.",
        "nothing": "Nothing clear to report.",
        "fallback": "Rough description: {summary}",
    },
    "hi": {
        "hazard": "सावधान: {where} {what}, {distance}।",
        "found": "{target} दिख रहा है: {where}।",
        "found_no_place": "{target} दिख रहा है।",
        "not_found": "{target} नहीं दिख रहा।",
        "uncertain": "पक्का नहीं है कि {target} यहाँ है या नहीं।",
        "no_text": "कोई पढ़ने लायक लिखावट नहीं है।",
        "nothing": "कुछ साफ़ नहीं दिख रहा।",
        "fallback": "मोटा विवरण: {summary}",
        "objects": "दिख रहा है: {objects}।",
    },
}
_NEAREST_FIRST = {"near": 0, "mid": 1, "far": 2}


def hazard_sentence(hazard: Hazard, lang: str) -> str:
    what = hazard.what.strip().rstrip(".")
    return PHRASES[lang]["hazard"].format(
        what=hindi.translate(what) if lang == "hi" else what,
        where=WHERE[lang][hazard.where],
        distance=DISTANCE[lang][hazard.distance],
    )


def hazard_cards(scene: Scene, lang: str = "en") -> list[dict]:
    """The warnings to give, nearest first, each one only once."""
    cards = {}
    for h in sorted(scene.hazards, key=lambda h: _NEAREST_FIRST[h.distance]):
        what = h.what.strip().rstrip(".")
        sentence = hazard_sentence(h, lang)
        # A dict keyed by sentence drops repeats (the model sometimes lists one hazard twice).
        cards.setdefault(sentence, {
            "sentence": sentence, "what": hindi.translate(what) if lang == "hi" else what,
            "where": h.where, "distance": h.distance,
        })
    return list(cards.values())


def object_names(scene: Scene, lang: str = "en", limit: int = 6) -> list[str]:
    """Names of the things seen, for display. Hindi uses the glossary where it can."""
    names = [hindi.translate(o.what) if lang == "hi" else o.what.strip() for o in scene.objects]
    return list(dict.fromkeys(n for n in names if n))[:limit]


def _short(summary: str) -> str:
    words = summary.split()
    return summary.strip() if len(words) <= MAX_SUMMARY_WORDS else " ".join(words[:MAX_SUMMARY_WORDS]) + "."


def build_speech(scene: Scene, mode: str, lang: str = "en", target: str = "",
                 find_result: FindResult | None = None, fallback: bool = False,
                 ) -> tuple[list[str], list[str]]:
    """Return (hazard sentences, other sentences). Hazards are nearest first.

    Objects and text are only spoken in the mode that asks for them. A fallback scene
    (plain text, no validated JSON) is spoken with a prefix that marks it as rough.
    """
    phrases = PHRASES[lang]
    hazards = [card["sentence"] for card in hazard_cards(scene, lang)]
    summary = _short(scene.summary)
    if lang == "hi" and not fallback:
        summary = _hindi_summary(scene) or summary

    if fallback:
        rest = [phrases["fallback"].format(summary=summary)] if summary else []
    elif mode == "read":
        lines = [line.strip() for line in scene.text if line.strip()]
        rest = lines or [phrases["no_text"]]
    elif mode == "find" and find_result is not None:
        name = hindi.translate(target) if lang == "hi" else target.strip()
        if find_result.status == "found":
            where = find_result.where.strip().rstrip(".")
            if lang == "hi":
                where = hindi.translate_place(where)
            key = "found" if where else "found_no_place"
            rest = [phrases[key].format(target=name, where=where)]
        else:
            rest = [phrases[find_result.status].format(target=name)]
    else:
        rest = [summary] if summary else []

    if not hazards and not rest:
        rest = [phrases["nothing"]]
    return hazards, rest


def _hindi_summary(scene: Scene) -> str:
    """A Hindi line built from the objects the glossary knows, or "" if it knows none.

    The model's free-text summary is English and cannot be translated reliably offline.
    """
    known = [hindi.translate(o.what) for o in scene.objects if hindi.is_known(o.what)]
    names = list(dict.fromkeys(known))[:MAX_OBJECTS_SPOKEN]
    return PHRASES["hi"]["objects"].format(objects=", ".join(names)) if names else ""


class RepeatFilter:
    """Drops sentences that were already spoken within the last `window_s` seconds."""

    def __init__(self, window_s: float, clock=time.monotonic):
        self.window_s = window_s
        self._clock = clock
        self._last_spoken: dict[str, float] = {}

    def remember(self, sentences: list[str]) -> None:
        now = self._clock()
        for sentence in sentences:
            self._last_spoken[sentence.lower()] = now

    def fresh(self, sentences: list[str]) -> list[str]:
        """Return the sentences not spoken recently, and remember them as spoken now."""
        now = self._clock()
        self._last_spoken = {k: t for k, t in self._last_spoken.items() if now - t < self.window_s}
        keep = [s for s in sentences if s.lower() not in self._last_spoken]
        self.remember(keep)
        return keep

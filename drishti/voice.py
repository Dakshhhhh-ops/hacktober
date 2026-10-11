"""Offline voice commands, so the app can be used without typing or tapping.

Speech is recognised on this machine with Vosk. The browser's built-in speech recognition
is not used because it sends the audio to a cloud service. Recognition is limited to a
small vocabulary of command words and everyday objects, which keeps it accurate in a noisy
room: anything else comes back as "[unk]" and is ignored.
"""
import json
import re

from . import config
from .hindi import GLOSSARY

SAMPLE_RATE = 16000
MAX_SECONDS = 8
MODELS = {"en": "vosk-model-small-en-us-0.15", "hi": "vosk-model-small-hi-0.22"}

# command -> words that trigger it
COMMANDS = {
    "en": {
        "describe": ["describe", "surroundings", "look", "around", "front", "see"],
        "read": ["read", "text"],
        "find": ["find", "where", "search", "locate"],
        "stop": ["stop", "quiet", "silence"],
        "repeat": ["repeat", "again"],
        "hindi": ["hindi"],
        "english": ["english"],
    },
    "hi": {
        "describe": ["बताओ", "देखो", "आसपास", "सामने"],
        "read": ["पढ़ो", "पढ़"],
        "find": ["खोजो", "ढूंढो", "ढूँढो", "कहां", "कहाँ"],
        # Several ways to say stop: with only three, the small model missed "रुको".
        "stop": ["रुको", "रुकिए", "रुक", "ठहरो", "बंद", "चुप", "बस", "शांत", "स्टॉप"],
        "repeat": ["दोबारा", "फिर"],
        "hindi": ["हिंदी", "हिन्दी"],
        "english": ["अंग्रेजी", "अंग्रेज़ी", "इंग्लिश"],
    },
}
# Small words that may surround a command and carry no meaning.
FILLERS = {
    "en": ["the", "a", "an", "my", "is", "are", "me", "for", "please", "what", "in", "of", "this", "it", "to"],
    "hi": ["मेरा", "मेरी", "मेरे", "है", "हैं", "क्या", "यह", "को", "का", "की", "के", "में", "करो", "जाओ"],
}
# Things a person might ask to find, beyond the hazard glossary.
EXTRA_OBJECTS = ["bottle", "water", "phone", "keys", "key", "bag", "wallet", "glasses", "shoe", "shoes",
                 "charger", "remote", "pen", "medicine", "umbrella", "watch", "mouse", "keyboard",
                 "exit", "toilet", "switch", "person", "helmet", "cup", "book", "laptop"]
# Hindi word a person might say -> the English name the vision model is asked for.
HINDI_OBJECTS = {
    "बोतल": "bottle", "पानी": "water", "कुर्सी": "chair", "दरवाजा": "door", "दरवाज़ा": "door",
    "चाबी": "keys", "फोन": "phone", "फ़ोन": "phone", "बैग": "bag", "किताब": "book", "मेज": "table",
    "मेज़": "table", "सीढ़ी": "stairs", "सीढ़ियां": "stairs", "लैपटॉप": "laptop", "कप": "cup",
    "गाड़ी": "car", "दवा": "medicine", "दवाई": "medicine", "चश्मा": "glasses", "घड़ी": "watch",
    "जूते": "shoes", "पेन": "pen", "आदमी": "person", "कुत्ता": "dog", "खिड़की": "window",
}

_models = {}


def vocabulary(lang: str) -> list[str]:
    """Every word the recogniser is allowed to hear for a language."""
    words = [w for group in COMMANDS[lang].values() for w in group] + FILLERS[lang]
    if lang == "en":
        objects = EXTRA_OBJECTS + [w for key in GLOSSARY for w in key.split()]
    else:
        objects = list(HINDI_OBJECTS)
    return list(dict.fromkeys(words + objects))


def _model(lang: str):
    """Load and cache the Vosk model for a language, or return None if it is not installed."""
    if lang not in _models:
        path = config.ROOT / "models" / MODELS[lang]
        model = None
        if path.is_dir():
            try:
                import vosk
                vosk.SetLogLevel(-1)
                model = vosk.Model(str(path))
            except Exception as err:  # missing package or a broken model folder
                print(f"[voice] speech model for '{lang}' could not be loaded: {err}")
        _models[lang] = model
    return _models[lang]


def available(lang: str = "en") -> bool:
    return _model(lang) is not None


def transcribe(pcm: bytes, lang: str = "en") -> str:
    """Recognise 16 kHz, 16-bit mono audio. Returns only words from the vocabulary."""
    model = _model(lang)
    if model is None:
        raise RuntimeError(f"No offline speech model is installed for '{lang}'.")
    import vosk
    grammar = json.dumps(vocabulary(lang) + ["[unk]"], ensure_ascii=False)
    recogniser = vosk.KaldiRecognizer(model, SAMPLE_RATE, grammar)
    recogniser.AcceptWaveform(pcm)
    text = json.loads(recogniser.FinalResult()).get("text", "")
    return " ".join(w for w in text.split() if w != "[unk]")


def parse(text: str, lang: str = "en") -> dict:
    """Turn recognised words into {"command": ..., "target": ...}.

    command is one of describe, read, find, stop, repeat, hindi, english, or "" when
    nothing was understood. target is the object to look for (find only), in English.
    Words that are not a command are kept as a possible target, so "bottle" on its own
    can answer the question "What are you looking for?".
    """
    words = re.findall(r"\w+", text.lower(), flags=re.UNICODE) if lang == "en" else text.split()
    command = ""
    command_words = set()
    for name, triggers in COMMANDS[lang].items():
        hits = [w for w in words if w in triggers]
        if hits:
            command_words.update(hits)
            # "stop" wins over everything; otherwise the first command mentioned wins.
            if name == "stop" or not command:
                command = name
    rest = [w for w in words if w not in command_words and w not in FILLERS[lang]]
    if lang == "hi":
        rest = [HINDI_OBJECTS.get(w, w) for w in rest]
    target = " ".join(dict.fromkeys(rest))
    if command not in ("", "find"):
        target = ""
    return {"command": command, "target": target}

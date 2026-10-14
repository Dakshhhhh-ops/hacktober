"""Offline voice commands, so the app can be used without typing or tapping.

Speech is recognised on this machine. The browser's built-in speech recognition is not
used because it sends the audio to a cloud service.

Two recognisers are supported, and the better one that is installed is used:

- Whisper (through faster-whisper): open vocabulary, good with accents, natural
  sentences and background noise, English and Hindi. Runs on the CPU.
- Vosk: much smaller and faster, but limited to a fixed list of command words and
  everyday objects, and noticeably weaker with real voices.
"""
import json
import re

from . import config
from .hindi import GLOSSARY

SAMPLE_RATE = 16000
MAX_SECONDS = 8
VOSK_MODELS = {"en": "vosk-model-small-en-us-0.15", "hi": "vosk-model-small-hi-0.22"}
WHISPER_DIR = config.ROOT / "models" / "whisper"
NO_SPEECH_LIMIT = 0.6    # drop a segment Whisper thinks is probably not speech
MIN_CONFIDENCE = -1.0    # drop a segment with a low average log-probability

# command -> words that trigger it. English triggers match as prefixes, so "describe",
# "described" and "describing" all count.
COMMANDS = {
    "en": {
        "describe": ["describ", "surrounding", "around", "front", "see"],
        "read": ["read", "text"],
        "find": ["find", "where", "search", "locate", "looking"],
        # Not "note": "find my notebook" must stay a find.
        "money": ["money", "rupee", "cash", "currency", "much"],
        "stop": ["stop", "quiet", "silence"],
        "repeat": ["repeat", "again"],
        "hindi": ["hindi"],
        "english": ["english"],
    },
    "hi": {
        "describe": ["बताओ", "बताइए", "देखो", "आसपास", "सामने", "डिस्क्राइब"],
        "read": ["पढ़ो", "पढ़", "पढ़िए", "रीड"],
        "find": ["खोजो", "ढूंढो", "ढूँढो", "कहां", "कहाँ", "फाइंड"],
        "money": ["पैसे", "पैसा", "नोट", "रुपये", "रुपए", "रुपया", "कितने", "मनी"],
        # Several ways to say stop: with only three, the small Vosk model missed "रुको".
        "stop": ["रुको", "रुकिए", "रुक", "ठहरो", "बंद", "चुप", "बस", "शांत", "स्टॉप"],
        "repeat": ["दोबारा", "फिर"],
        "hindi": ["हिंदी", "हिन्दी"],
        "english": ["अंग्रेजी", "अंग्रेज़ी", "इंग्लिश"],
    },
}
# Small words that may surround a command and carry no meaning.
FILLERS = {
    "en": ["the", "a", "an", "my", "is", "are", "me", "for", "please", "what", "in", "of", "this", "it",
           "to", "can", "you", "i", "am", "want", "need", "now", "hey", "there", "that", "do", "does",
           "tell", "show", "and", "at", "on", "out", "look"],
    "hi": ["मेरा", "मेरी", "मेरे", "है", "हैं", "क्या", "यह", "को", "का", "की", "के", "में", "करो", "जाओ",
           "मुझे", "जरा", "ज़रा", "कृपया", "और"],
}
# Things a person might ask to find, beyond the hazard glossary (used for Vosk's word list).
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
# Shown to Whisper as context, which makes the command words more likely to be heard right.
WHISPER_HINTS = {
    "en": "Voice commands: describe. read. find my water bottle. where is the door. how much money. stop. repeat. Hindi. English.",
    "hi": "आवाज़ के आदेश: बताओ। पढ़ो। मेरी बोतल कहां है। खोजो। कितने पैसे हैं। रुको। बस। दोबारा। हिंदी। अंग्रेजी।",
}

_whisper = None
_whisper_checked = False
_vosk_models = {}


def vocabulary(lang: str) -> list[str]:
    """Every word the Vosk recogniser is allowed to hear for a language."""
    words = [w for group in COMMANDS[lang].values() for w in group] + FILLERS[lang]
    if lang == "en":
        # Vosk needs whole words, so expand the prefixes used for matching.
        words += ["describe", "surroundings"]
        objects = EXTRA_OBJECTS + [w for key in GLOSSARY for w in key.split()]
    else:
        objects = list(HINDI_OBJECTS)
    return list(dict.fromkeys(words + objects))


def _whisper_model():
    """Load and cache Whisper, or return None if it is not installed."""
    global _whisper, _whisper_checked
    if not _whisper_checked:
        _whisper_checked = True
        if WHISPER_DIR.is_dir():
            try:
                from faster_whisper import WhisperModel
                # local_files_only: never contact the network at run time.
                _whisper = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8",
                                        cpu_threads=config.WHISPER_THREADS,
                                        download_root=str(WHISPER_DIR), local_files_only=True)
            except Exception as err:  # missing package or model files
                print(f"[voice] Whisper could not be loaded: {err}")
    return _whisper


def _vosk_model(lang: str):
    """Load and cache the Vosk model for a language, or return None if it is not installed."""
    if lang not in _vosk_models:
        path = config.ROOT / "models" / VOSK_MODELS[lang]
        model = None
        if path.is_dir():
            try:
                import vosk
                vosk.SetLogLevel(-1)
                model = vosk.Model(str(path))
            except Exception as err:  # missing package or a broken model folder
                print(f"[voice] Vosk model for '{lang}' could not be loaded: {err}")
        _vosk_models[lang] = model
    return _vosk_models[lang]


# Which recogniser to try first for each language. Measured with synthesised speech:
# Whisper base was much better for English sentences, but for short Hindi commands the
# word-list recogniser was better (7 of 8 against 4 of 8).
ENGINE_ORDER = {"en": ("whisper", "vosk"), "hi": ("vosk", "whisper")}


def engines(lang: str = "en") -> list[str]:
    """The installed recognisers for a language, best first."""
    installed = {"whisper": _whisper_model() is not None, "vosk": _vosk_model(lang) is not None}
    return [name for name in ENGINE_ORDER[lang] if installed[name]]


def engine(lang: str = "en") -> str | None:
    """The recogniser tried first: "whisper", "vosk" or None."""
    return next(iter(engines(lang)), None)


def available(lang: str = "en") -> bool:
    return engine(lang) is not None


def transcribe(pcm: bytes, lang: str = "en", using: str | None = None) -> str:
    """Recognise 16 kHz, 16-bit mono audio and return the words heard."""
    using = using or engine(lang)
    if using == "whisper":
        import numpy as np
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = _whisper_model().transcribe(
            audio, language=lang, beam_size=5, initial_prompt=WHISPER_HINTS[lang],
            condition_on_previous_text=False, without_timestamps=True, vad_filter=True)
        # On noise Whisper can invent text, sometimes by repeating the hint. Keep only
        # segments it is reasonably sure contain speech.
        heard = [s.text.strip() for s in segments
                 if s.no_speech_prob < NO_SPEECH_LIMIT and s.avg_logprob > MIN_CONFIDENCE]
        return " ".join(heard).strip()
    if using == "vosk":
        import vosk
        grammar = json.dumps(vocabulary(lang) + ["[unk]"], ensure_ascii=False)
        recogniser = vosk.KaldiRecognizer(_vosk_model(lang), SAMPLE_RATE, grammar)
        recogniser.AcceptWaveform(pcm)
        text = json.loads(recogniser.FinalResult()).get("text", "")
        return " ".join(w for w in text.split() if w != "[unk]")
    raise RuntimeError(f"No offline speech model is installed for '{lang}'.")


def recognise(pcm: bytes, lang: str = "en") -> dict:
    """Recognise a spoken command: {"text", "command", "target", "engine"}.

    Tries each installed recogniser in order and stops at the first that hears a command.
    If none does, the first thing heard is returned so the page can show it.
    """
    first = None
    for name in engines(lang):
        text = transcribe(pcm, lang, name)
        result = {"text": text, **parse(text, lang), "engine": name}
        if result["command"]:
            return result
        if first is None and text:
            first = result
    return first or {"text": "", "command": "", "target": "", "engine": engine(lang)}


# One-word commands that are often misheard by a single sound: "top" for "stop".
_SINGLE_WORDS = {"stop": "stop", "read": "read", "find": "find", "describe": "describe", "repeat": "repeat",
                 "money": "money"}


def _one_edit_apart(a: str, b: str) -> bool:
    """True if the words differ by one inserted, removed or changed letter."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:] or (len(a) == len(b) and a[i + 1:] == b[i + 1:])


def _is_trigger(word: str, triggers: list[str], lang: str) -> bool:
    return any(word.startswith(t) for t in triggers) if lang == "en" else word in triggers


def parse(text: str, lang: str = "en") -> dict:
    """Turn recognised words into {"command": ..., "target": ...}.

    command is one of describe, read, find, money, stop, repeat, hindi, english, or "" when
    nothing was understood. target is the object to look for (find only), in English.
    Words that are not a command are kept as a possible target, so "bottle" on its own
    can answer the question "What are you looking for?".
    """
    # \w does not cover Devanagari vowel signs, so Hindi is split on spaces and punctuation.
    words = (re.findall(r"[a-z0-9']+", text.lower()) if lang == "en"
             else [w for w in re.split(r"[\s।,.?!\"]+", text) if w])
    command = ""
    command_words = set()
    for name, triggers in COMMANDS[lang].items():
        hits = [w for w in words if _is_trigger(w, triggers, lang)]
        if hits:
            command_words.update(hits)
            # "stop" wins over everything; otherwise the first command mentioned wins.
            if name == "stop" or not command:
                command = name
    if not command and lang == "en" and len(words) == 1 and len(words[0]) >= 3:
        # A lone word one letter away from a command is taken as that command.
        near = [name for word, name in _SINGLE_WORDS.items() if _one_edit_apart(words[0], word)]
        if near:
            return {"command": near[0], "target": ""}
    rest = [w for w in words if w not in command_words and w not in FILLERS[lang]]
    if lang == "hi":
        rest = [HINDI_OBJECTS.get(w, w) for w in rest]
    target = " ".join(dict.fromkeys(rest))
    if command not in ("", "find"):
        target = ""
    # Three or more different commands in one breath is not a request: it is noise, or
    # the recogniser echoing its hint. Only an explicit stop is still honoured.
    different = sum(any(_is_trigger(w, triggers, lang) for w in words) for triggers in COMMANDS[lang].values())
    if different >= 3 and command != "stop":
        return {"command": "", "target": ""}
    return {"command": command, "target": target}

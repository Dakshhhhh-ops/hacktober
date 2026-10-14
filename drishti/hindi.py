"""Hindi wording from a fixed glossary.

The default 2B vision model cannot write usable Hindi (measured: its translations were
mostly nonsense), so it is always asked to answer in English. For Hindi output the app
looks up the hazard or object in this glossary. A phrase with no known word is left in
English rather than guessed. Adjectives are dropped: "red plastic barriers" -> "बैरिकेड".
"""
import re

# English noun (singular or as commonly written) -> Hindi. Longer keys are matched first.
GLOSSARY = {
    # hazards on the ground
    "wet floor": "गीला फ़र्श", "slippery floor": "फिसलन वाला फ़र्श", "puddle": "जमा हुआ पानी",
    "water": "पानी", "pothole": "गड्ढा", "hole": "गड्ढा", "manhole": "खुला मैनहोल",
    "uneven pavement": "ऊबड़-खाबड़ ज़मीन", "uneven": "ऊबड़-खाबड़ ज़मीन", "crack": "दरार",
    "curb": "फ़ुटपाथ का किनारा", "kerb": "फ़ुटपाथ का किनारा", "ledge": "किनारा", "edge": "किनारा",
    "drop": "ढलान", "cable": "तार", "wire": "तार", "stone": "पत्थर", "rock": "पत्थर",
    "glass": "काँच", "fire": "आग",
    # stairs and doors
    "staircase": "सीढ़ियाँ", "stairway": "सीढ़ियाँ", "stairs": "सीढ़ियाँ", "stair": "सीढ़ियाँ",
    "steps": "सीढ़ियाँ", "step": "सीढ़ी", "escalator": "एस्केलेटर", "ramp": "ढलान",
    "open door": "खुला दरवाज़ा", "doorway": "दरवाज़ा", "door": "दरवाज़ा", "gate": "गेट",
    # things in the way
    "traffic cone": "ट्रैफ़िक कोन", "cone": "ट्रैफ़िक कोन", "barricade": "बैरिकेड",
    "barrier": "बैरिकेड", "fence": "बाड़", "railing": "रेलिंग", "handrail": "रेलिंग",
    "warning sign": "चेतावनी बोर्ड", "caution sign": "चेतावनी बोर्ड", "signboard": "बोर्ड",
    "sign": "बोर्ड", "pole": "खंभा", "pillar": "खंभा", "post": "खंभा", "wall": "दीवार",
    "bucket": "बाल्टी", "bin": "कूड़ेदान", "box": "डिब्बा", "bag": "बैग", "backpack": "बैग",
    "chair": "कुर्सी", "table": "मेज़", "desk": "मेज़", "bench": "बेंच", "bed": "बिस्तर",
    "sofa": "सोफ़ा", "couch": "सोफ़ा", "tree": "पेड़", "plant": "पौधा",
    # vehicles, people, animals
    "bicycle": "साइकिल", "bike": "साइकिल", "motorcycle": "मोटरसाइकिल", "scooter": "स्कूटर",
    "car": "गाड़ी", "vehicle": "गाड़ी", "suv": "गाड़ी", "bus": "बस", "truck": "ट्रक",
    "auto": "ऑटो", "people": "लोग", "person": "व्यक्ति", "pedestrian": "व्यक्ति",
    "man": "आदमी", "woman": "महिला", "child": "बच्चा", "dog": "कुत्ता", "cow": "गाय",
    "animal": "जानवर",
    # everyday objects
    "bottle": "बोतल", "cup": "कप", "phone": "फ़ोन", "laptop": "लैपटॉप", "key": "चाबी",
    "book": "किताब", "window": "खिड़की", "floor": "फ़र्श", "road": "सड़क", "lamp": "बत्ती",
    "light": "बत्ती", "fan": "पंखा", "screen": "स्क्रीन", "corridor": "गलियारा",
    "hallway": "गलियारा", "room": "कमरा",
}
# Words for where something is, used in Find mode.
PLACES = {
    "left": "बाईं ओर", "right": "दाईं ओर", "center": "बीच में", "centre": "बीच में",
    "middle": "बीच में", "ahead": "सामने", "front": "सामने", "below": "नीचे", "floor": "फ़र्श पर",
    "ground": "ज़मीन पर", "table": "मेज़ पर", "desk": "मेज़ पर", "top": "ऊपर", "bottom": "नीचे",
    "behind": "पीछे", "near": "पास",
}

_KEYS = sorted(GLOSSARY, key=len, reverse=True)


def _has_word(phrase: str, word: str) -> bool:
    # Whole words only, allowing a plural ending: "barriers" matches "barrier".
    return re.search(rf"\b{re.escape(word)}(s|es)?\b", phrase) is not None


def translate(phrase: str) -> str:
    """Hindi for the main noun in an English phrase, or the phrase unchanged if unknown."""
    lowered = phrase.lower()
    for key in _KEYS:
        if _has_word(lowered, key):
            return GLOSSARY[key]
    return phrase.strip()


def is_known(phrase: str) -> bool:
    return translate(phrase) != phrase.strip()


def translate_place(where: str) -> str:
    """'on the table, to the left' -> 'मेज़ पर, बाईं ओर'. Unknown wording is left as it is."""
    lowered = where.lower()
    found = [(lowered.find(word), hindi) for word, hindi in PLACES.items() if _has_word(lowered, word)]
    parts = list(dict.fromkeys(hindi for _, hindi in sorted(found)))
    return ", ".join(parts) if parts else where.strip()

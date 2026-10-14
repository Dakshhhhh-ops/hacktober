"""Fast object detection with YOLOX, run on the CPU through onnxruntime.

The vision-language model takes seconds and can miss an obvious hazard. YOLOX finds
people, vehicles and animals in tens of milliseconds, so it is used two ways:

- In walk mode the page calls it several times a second for quick warnings about people,
  vehicles and animals that are close or straight ahead.
- In Find mode, for everyday objects it knows (a bottle, a phone, a bag), it guides the
  person live: "bottle on the left", then "bottle ahead, near" as they turn.
- The evaluation can add its detections to the model's answers (run_eval.py --detector).
  Measured, that found no hazard the model had missed and added a false "train", so the
  app does not do it in Surroundings mode.

YOLOX (Megvii, Apache-2.0) is trained on COCO's 80 everyday classes. It knows nothing about
potholes, open drains or stairs; those still come only from the vision-language model.
The model file lives in models/yolox/ (see the README); without it detection is off.
"""
import threading
from dataclasses import dataclass

from . import config
from .schema import Hazard

INPUT_SIZE = 416
MIN_SCORE = 0.45
DECODE_MIN_SCORE = 0.35  # what detect() keeps; warnings use MIN_SCORE, finding a little lower
NMS_IOU = 0.45

# COCO class names, in the model's output order.
COCO = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush",
)
# Things worth a warning when they are in the way, with the word that is spoken.
# The words are deliberately general: COCO has no auto-rickshaw, which it calls a truck or a
# bus, and a cow seen close up can come out as a dog. "Vehicle" and "animal" are never wrong.
# Furniture is left out: in a room it is everywhere and would drown out real warnings.
# Trains are left out too: red-and-white plastic barriers came out as a train, and on a
# platform the danger is the edge, which the vision-language model reports.
HAZARD_NAMES = {
    "person": "person", "bicycle": "bicycle", "motorcycle": "motorcycle",
    "car": "vehicle", "bus": "vehicle", "truck": "vehicle",
    "dog": "animal", "cow": "animal", "horse": "animal", "sheep": "animal",
    "elephant": "animal", "cat": "animal",
}
# Words the vision model might use for the same thing, so a detection it already
# mentioned is not added twice.
SAME_THING = {
    "person": ("person", "people", "man", "men", "woman", "women", "child", "children", "boy",
               "girl", "pedestrian", "crowd", "someone", "worker", "vendor"),
    "bicycle": ("bicycle", "bike", "cycle", "cyclist"),
    "motorcycle": ("motorcycle", "motorbike", "bike", "scooter", "moped", "rider"),
    "vehicle": ("vehicle", "car", "bus", "truck", "lorry", "van", "auto", "rickshaw", "taxi",
                "jeep", "suv", "traffic", "tempo", "tuk"),
    "animal": ("animal", "cow", "bull", "ox", "cattle", "buffalo", "dog", "puppy", "horse",
               "donkey", "goat", "sheep", "elephant", "cat", "calf"),
}


@dataclass
class Detection:
    label: str          # COCO class name
    score: float
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 as fractions of the frame

    @property
    def where(self) -> str:
        """left / ahead / right, from the middle of the box."""
        middle = (self.box[0] + self.box[2]) / 2
        return "left" if middle < 0.33 else "right" if middle > 0.67 else "ahead"

    @property
    def distance(self) -> str:
        """A rough guess from how much of the frame the object fills. Not a measurement."""
        height = self.box[3] - self.box[1]
        width = self.box[2] - self.box[0]
        if height > 0.45 or width * height > 0.15:
            return "near"
        if height > 0.18:
            return "mid"
        return "far"

    def as_hazard(self) -> Hazard:
        return Hazard(what=HAZARD_NAMES[self.label], where=self.where, distance=self.distance)


_session = None
_session_lock = threading.Lock()
_tried = False


def _load():
    global _session, _tried
    with _session_lock:
        if not _tried:
            _tried = True
            path = config.DETECTOR_MODEL
            if path.exists():
                try:
                    import onnxruntime
                    options = onnxruntime.SessionOptions()
                    options.intra_op_num_threads = config.DETECTOR_THREADS
                    _session = onnxruntime.InferenceSession(
                        str(path), options, providers=["CPUExecutionProvider"])
                except Exception as err:  # missing package or a broken file
                    print(f"[detector] could not load {path.name}: {err}")
            else:
                print(f"[detector] {path} not found; object detection is off")
    return _session


def available() -> bool:
    return _load() is not None


def _grids(input_size: int = INPUT_SIZE):
    """Anchor centres and strides for a square YOLOX input (strides 8, 16, 32)."""
    import numpy as np
    grids, strides = [], []
    for stride in (8, 16, 32):
        size = input_size // stride
        ys, xs = np.meshgrid(np.arange(size), np.arange(size), indexing="ij")
        grids.append(np.stack((xs, ys), axis=-1).reshape(-1, 2))
        strides.append(np.full((size * size, 1), stride))
    return np.concatenate(grids), np.concatenate(strides)


def decode(raw, ratio: float, width: int, height: int, min_score: float = MIN_SCORE,
           input_size: int = INPUT_SIZE):
    """Turn the network's (N, 85) output into Detections in frame fractions."""
    import cv2
    import numpy as np
    grids, strides = _grids(input_size)
    xy = (raw[:, :2] + grids) * strides
    wh = np.exp(raw[:, 2:4]) * strides
    scores = raw[:, 4:5] * raw[:, 5:]
    classes = scores.argmax(axis=1)
    best = scores[np.arange(len(scores)), classes]
    keep = best >= min_score
    if not keep.any():
        return []
    xy, wh, classes, best = xy[keep], wh[keep], classes[keep], best[keep]
    boxes = np.concatenate((xy - wh / 2, wh), axis=1) / ratio  # x, y, w, h in frame pixels
    chosen = cv2.dnn.NMSBoxesBatched(boxes.tolist(), best.tolist(), classes.tolist(),
                                     min_score, NMS_IOU)
    found = []
    for i in np.array(chosen).reshape(-1):
        x, y, w, h = boxes[i]
        box = (max(0.0, x / width), max(0.0, y / height),
               min(1.0, (x + w) / width), min(1.0, (y + h) / height))
        found.append(Detection(COCO[classes[i]], round(float(best[i]), 3),
                               tuple(round(float(v), 4) for v in box)))
    return sorted(found, key=lambda d: -d.score)


def detect(image_bytes: bytes) -> list[Detection]:
    """Every object found in a JPEG or PNG frame, best first. [] if detection is off."""
    session = _load()
    if session is None:
        return []
    import cv2
    import numpy as np
    image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return []
    height, width = image.shape[:2]
    # 416 for YOLOX-Nano and -Tiny, 640 for the larger ones: read it from the model.
    size = session.get_inputs()[0].shape[2]
    size = size if isinstance(size, int) else INPUT_SIZE
    ratio = min(size / height, size / width)
    resized = cv2.resize(image, (int(width * ratio), int(height * ratio)),
                         interpolation=cv2.INTER_LINEAR)
    padded = np.full((size, size, 3), 114, np.uint8)
    padded[:resized.shape[0], :resized.shape[1]] = resized
    blob = padded.transpose(2, 0, 1)[None].astype(np.float32)  # BGR, 0-255, as trained
    raw = session.run(None, {session.get_inputs()[0].name: blob})[0][0]
    return decode(raw, ratio, width, height, DECODE_MIN_SCORE, size)


_NEAREST_FIRST = {"near": 0, "mid": 1, "far": 2}

# What a person might ask to find -> the COCO classes that count as it. Longer names are
# tried first, so "water bottle" is a bottle and "laptop bag" is a bag, not a laptop.
FINDABLE = {
    "water bottle": ("bottle",), "bottle": ("bottle",),
    "cup": ("cup",), "mug": ("cup",), "glass": ("cup", "wine glass"), "tumbler": ("cup",),
    "mobile phone": ("cell phone",), "cell phone": ("cell phone",), "phone": ("cell phone",),
    "mobile": ("cell phone",),
    "laptop bag": ("backpack", "handbag", "suitcase"), "school bag": ("backpack",),
    "backpack": ("backpack",), "handbag": ("handbag",), "purse": ("handbag",),
    "suitcase": ("suitcase",), "bag": ("backpack", "handbag", "suitcase"),
    "laptop": ("laptop",), "keyboard": ("keyboard",), "mouse": ("mouse",),
    "remote": ("remote",), "book": ("book",), "chair": ("chair",), "bench": ("bench",),
    "sofa": ("couch",), "couch": ("couch",), "bed": ("bed",), "table": ("dining table",),
    "tv": ("tv",), "television": ("tv",), "clock": ("clock",), "umbrella": ("umbrella",),
    "toilet": ("toilet",), "sink": ("sink",), "fridge": ("refrigerator",),
    "refrigerator": ("refrigerator",), "microwave": ("microwave",), "bowl": ("bowl",),
    "spoon": ("spoon",), "knife": ("knife",), "fork": ("fork",), "scissors": ("scissors",),
    "toothbrush": ("toothbrush",), "plant": ("potted plant",), "person": ("person",),
    "dog": ("dog",), "cat": ("cat",), "bicycle": ("bicycle",), "cycle": ("bicycle",),
    "car": ("car",), "bus": ("bus",), "scooter": ("motorcycle",), "bike": ("motorcycle", "bicycle"),
}
_FINDABLE_KEYS = sorted(FINDABLE, key=len, reverse=True)
FIND_MIN_SCORE = 0.35  # lower than for warnings: the person is told it is a guess as they turn


def find_match(target: str) -> tuple[str, tuple[str, ...]] | None:
    """(the object's name, its COCO classes) for what the person asked to find, or None
    if the detector does not know it; then the vision-language model is asked instead.

    The request must END with the object: "my water bottle" is a bottle, but "car keys",
    "phone charger" and "table fan" are not a car, a phone and a table.
    """
    words = " " + " ".join(target.lower().replace("-", " ").split()) + " "
    for key in _FINDABLE_KEYS:
        if words.endswith(f" {key} ") or words.endswith(f" {key}s "):
            return key, FINDABLE[key]
    return None


def find_labels(target: str) -> tuple[str, ...] | None:
    match = find_match(target)
    return match[1] if match else None


def locate(detections: list[Detection], labels: tuple[str, ...]) -> Detection | None:
    """The most confident detection of the thing being looked for, or None."""
    matches = [d for d in detections if d.label in labels and d.score >= FIND_MIN_SCORE]
    return max(matches, key=lambda d: d.score, default=None)


def hazards(detections: list[Detection], include_far: bool = False) -> list[Hazard]:
    """The detections worth a warning, nearest first, one per kind of thing and direction.

    A crowd is "person ahead, near", not ten people. Far objects are left out unless asked
    for: they are rarely in the way and would bury the warnings that matter.
    """
    chosen: dict[tuple[str, str], Hazard] = {}
    for d in detections:
        if d.label not in HAZARD_NAMES or d.score < MIN_SCORE or (d.distance == "far" and not include_far):
            continue
        hazard = d.as_hazard()
        key = (hazard.what, hazard.where)
        if key not in chosen or _NEAREST_FIRST[hazard.distance] < _NEAREST_FIRST[chosen[key].distance]:
            chosen[key] = hazard
    return sorted(chosen.values(), key=lambda h: _NEAREST_FIRST[h.distance])


def walk_warnings(detections: list[Detection]) -> list[Hazard]:
    """What to say while walking: anything near, and things at mid distance straight ahead."""
    return [h for h in hazards(detections)
            if h.distance == "near" or (h.distance == "mid" and h.where == "ahead")]


def _mentions(phrase: str, name: str) -> bool:
    words = phrase.lower().replace("-", " ").split()
    return any(w.startswith(s) for w in words for s in SAME_THING[name])


def missing_from(model_hazards: list[Hazard], detected: list[Hazard]) -> list[Hazard]:
    """Detected hazards the vision model did not mention at all."""
    return [h for h in detected if not any(_mentions(m.what, h.what) for m in model_hazards)]

"""Settings, read from environment variables or a .env file in the project root.

See .env.example for the full list. Real environment variables win over .env.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader: KEY=VALUE lines, # comments. No new dependency needed."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")


def _env(name, default, cast=str):
    return cast(os.environ.get(name, default))


# Vision-language model, served by Ollama on this machine.
OLLAMA_URL = _env("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = _env("OLLAMA_MODEL", "qwen3-vl:2b")
VLM_TIMEOUT_S = _env("DRISHTI_VLM_TIMEOUT_S", 120, float)
MAX_TOKENS = _env("DRISHTI_MAX_TOKENS", 400, int)

# The web server only listens on this machine by default.
HOST = _env("DRISHTI_HOST", "127.0.0.1")
PORT = _env("DRISHTI_PORT", 8000, int)
MAX_IMAGE_BYTES = _env("DRISHTI_MAX_IMAGE_BYTES", 4 * 1024 * 1024, int)
MAX_TARGET_CHARS = 80

# Automatic monitoring (experimental). The browser shrinks each frame to 16x16 grey
# pixels; the threshold is the mean pixel difference (0-255) from the last described frame.
CHANGE_THRESHOLD = _env("DRISHTI_CHANGE_THRESHOLD", 12, float)
MIN_INTERVAL_S = _env("DRISHTI_MIN_INTERVAL_S", 4, float)
# The same sentence is not spoken again automatically within this many seconds.
REPEAT_SUPPRESS_S = _env("DRISHTI_REPEAT_SUPPRESS_S", 20, float)

# Offline text-to-speech voices (file names without .onnx, inside voices/).
PIPER_VOICES = {
    "en": _env("PIPER_VOICE_EN", "en_US-lessac-medium"),
    "hi": _env("PIPER_VOICE_HI", "hi_IN-pratham-medium"),
}
ESPEAK_VOICES = {"en": "en", "hi": "hi"}

PROMPTS_DIR = ROOT / "prompts"
WEB_DIR = ROOT / "web"
VOICES_DIR = ROOT / "voices"
LATENCY_CSV = ROOT / "logs" / "latency.csv"

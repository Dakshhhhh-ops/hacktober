"""Offline text-to-speech: Piper if a voice is installed, otherwise espeak-ng.

Returns WAV bytes, or None when neither engine is available. The web page then falls
back to the browser's built-in voice.
"""
import io
import shutil
import subprocess
import wave

from . import config

_piper_voices = {}


def _piper_voice(lang: str):
    """Load and cache the Piper voice for a language, or return None."""
    if lang in _piper_voices:
        return _piper_voices[lang]
    voice = None
    model = config.VOICES_DIR / f"{config.PIPER_VOICES[lang]}.onnx"
    if model.exists():
        try:
            from piper import PiperVoice
            voice = PiperVoice.load(str(model))
        except Exception as err:  # missing package or a broken voice file
            print(f"[tts] Piper voice for '{lang}' could not be loaded: {err}")
    _piper_voices[lang] = voice
    return voice


def engine(lang: str = "en") -> str | None:
    if _piper_voice(lang) is not None:
        return "piper"
    if shutil.which("espeak-ng"):
        return "espeak-ng"
    return None


def synthesize(text: str, lang: str = "en") -> bytes | None:
    voice = _piper_voice(lang)
    if voice is not None:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            # piper-tts 1.3 renamed synthesize() to synthesize_wav().
            if hasattr(voice, "synthesize_wav"):
                voice.synthesize_wav(text, wav)
            else:
                voice.synthesize(text, wav)
        return buffer.getvalue()

    if shutil.which("espeak-ng"):
        done = subprocess.run(
            ["espeak-ng", "-v", config.ESPEAK_VOICES[lang], "--stdout", text],
            capture_output=True, timeout=30,
        )
        if done.returncode == 0 and done.stdout:
            return done.stdout
    return None

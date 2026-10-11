"""Start DrishtiAI:  python -m drishti"""
import uvicorn

from . import config, tts, vlm


def main() -> None:
    ok, message, fix = vlm.check_model()
    print(f"[model] {message} {fix}".rstrip())
    for lang in ("en", "hi"):
        # Loading a Piper voice takes a few seconds, so do it before the first request.
        print(f"[tts] {lang}: {tts.engine(lang) or 'no offline voice installed'}")
    print(f"Open http://{config.HOST}:{config.PORT} in your browser.")
    uvicorn.run("drishti.server:app", host=config.HOST, port=config.PORT, log_level="warning")


if __name__ == "__main__":
    main()

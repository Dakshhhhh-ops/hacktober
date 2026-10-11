# DrishtiAI

An offline scene-description assistant for people with visual impairments. A webcam frame
goes to an open-weight vision-language model running on your own machine through Ollama;
the answer comes back as validated JSON and is spoken aloud, hazards first, in English or
Hindi.

Built at Hacktoberfest Hack Day Hamirpur x ISTE NITH (11 October 2026) for the Best
Open-Source AI Project track.

> **Status: work in progress.** The pipeline, web page and unit tests are in place. The
> real-model smoke test, evaluation results and full documentation are being added today.

## Quick start

```
ollama pull qwen3-vl:2b
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m piper.download_voices en_US-lessac-medium hi_IN-pratham-medium --download-dir voices
.venv\Scripts\python -m drishti
```

Then open http://127.0.0.1:8000 and press Space.

## Tests

```
.venv\Scripts\python -m unittest discover -s tests -t .
node --test tests/gate.test.mjs
```

## Safety

DrishtiAI is an experimental aid. It can be wrong or miss hazards. It does not replace a
cane, a guide dog or a human guide.

## License

MIT for this project's code. See [LICENSE](LICENSE). The model weights and voices have
their own licences, which the full README will list.

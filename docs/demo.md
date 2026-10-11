# Demo script (2 to 3 minutes)

A rehearsed walk-through for judges. Everything shown is live; nothing is pre-recorded
or canned. Set the scene up safely: use a chair, a bag or a printed sign as the "hazard",
never a real risk to a person.

## Before you start

1. Ollama is running and `ollama list` shows the model.
2. `python -m drishti` is running and http://127.0.0.1:8000 is open with the camera allowed.
3. Press Space once so the model is loaded. The first call is the slow one.
4. Have ready: a printed label or sign, and one object to find (a water bottle).
5. Turn Wi-Fi **off**. Leave it off for the whole demo.

## The walk-through

| Step | Do | Say |
| --- | --- | --- |
| 1 | Show the Wi-Fi icon is off, then the top-right pill on the page. | "There is no internet. The model named here is running on this laptop through Ollama." |
| 2 | Point the camera at a chair or bag in the walkway. Press **Space**. | "It warns about hazards first, then gives one line about the scene." |
| 3 | Point at the line under the answer. | "That is the measured time inside the model, and the round trip." |
| 4 | Press **2**, hold up the printed label, press **Space**. | "Read mode. It reads what is visible and does not guess missing words." |
| 5 | Press **V**, wait for "Voice commands on", then say **"find my water bottle"**. | "No typing and no tapping: speech is recognised on this laptop too. Find answers found, not found or uncertain." |
| 6 | Press **L**, then **1**, then **Space**. | "The same scene in Hindi, with a separate offline Hindi voice." |
| 7 | Open "Model output (JSON)". | "This is the validated JSON. If the model returns invalid JSON, it is retried once, then marked as a rough description. Hazards are never invented." |
| 8 | In a terminal: `python eval/run_eval.py`, or open `eval/results.md`. | "Missed hazards are counted on their own line, because that is the dangerous failure." |
| 9 | Show the repository: LICENSE, `skill/describe-scene/SKILL.md`, the green test run. | "MIT code, an Apache-2.0 model, an Agent Skill on the same pipeline, and tests that run on every push." |

## If something goes wrong

- **The page says the model is not ready**: read the fix it shows. Usually Ollama is not
  running; open the Ollama app.
- **No sound**: check the volume slider and the laptop volume. The text of the answer is
  always on screen.
- **A wrong or missing warning**: say so. It is a 2-billion-parameter model, and the
  evaluation table states how often this happens. That honesty is part of the project.

## What not to claim

- That it is safe to navigate with. It is an experimental aid.
- That it measures distance. "Near" and "far" are rough visual judgements.
- That auto-monitor watches continuously. It skips frames that look alike.

# Evaluation

```
python eval/run_eval.py
```

This runs every image listed in `labels.csv` through the same `drishti.vlm.describe()`
pipeline the app uses, then writes:

- `results.json`: every prediction next to its ground-truth label, plus the metrics.
- `results.md`: the results table that the main README shows.

Ollama must be running with the configured model. Nothing here is mocked.

## Label format

`labels.csv` has three columns. The labels are written by a person looking at the photo;
they are the ground truth. The model's answers are never used as labels.

| Column | Meaning |
| --- | --- |
| `image` | File name inside `eval/images/`. |
| `hazards_true` | Physical hazards a careful person would warn about, separated by `;`. Leave empty if there are none. Give synonyms for one hazard with a vertical bar. |
| `text_true` | The text a person can read in the photo, as one string. Leave empty to skip the reading test for this image. |

Example:

```
image,hazards_true,text_true
stairs_down.jpg,stairs|steps|staircase,
wet_floor_sign.jpg,wet floor|slippery floor,CAUTION WET FLOOR
empty_corridor.jpg,,
medicine_strip.jpg,,Paracetamol Tablets IP 500 mg
```

Use the first synonym as the canonical name; it is the one shown in the results.

## Matching rules

**Hazards.** A hazard the model reported matches a labelled hazard when, after lowercasing,
removing punctuation and dropping a plural "s", one phrase contains the other or their
similarity (`difflib.SequenceMatcher`) is at least 0.75. Any synonym may match. Each
reported hazard can satisfy one label only. Direction and distance are not scored.

- **Detected**: a labelled hazard that some reported hazard matched.
- **Missed** (false negative): a labelled hazard nothing matched. This is the dangerous
  failure, so the count is reported on its own line.
- **False alarm**: a reported hazard that matched no label.
- **Hazard recall** = detected / labelled hazards.
- **False alarms per image** = false alarms / images evaluated.
- **False-alarm rate** = false alarms / all hazards the model reported. It answers "when
  the app warns, how often is the warning not in the labels?"

A fallback answer (plain text, no validated JSON) reports no hazards, so every labelled
hazard in that image counts as missed.

**Text.** For images with `text_true`, the image is run again in Read mode. Both strings
are lowercased, punctuation is removed and spaces are collapsed; similarity is the
`SequenceMatcher` ratio. A similarity of 0.80 or more counts as read correctly.

**Latency.** Time spent inside the vision model per request, in milliseconds, including a
retry if one happened. The median and the 95th percentile (nearest rank) are reported.

## Limits of this evaluation

- The image set is small and was collected by the author in one place. The numbers
  describe this set only.
- Label matching is by words. A correct warning phrased very differently from the label
  can be scored as a miss plus a false alarm; check `results.json` when a number looks odd.
- Whether a hazard was confidently *absent* is not measured, and the model's own
  confidence is never used as evidence.

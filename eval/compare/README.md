# Model comparison

Each model was run on each image set with the same prompts and code. The prompts were
written against the tuning set, so the held-out numbers are the fairer estimate. Latency
is the median time inside the model on an RTX 4050 Laptop GPU (6 GB), model already loaded.

| Model | Set | Hazard recall | Missed | Clear scenes with a false warning | Text read | Money right | JSON fallbacks | Median latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `gemma3:4b` | tuning | 80% (12/15) | 3 | 2/4 | 14/15 |  | 0 | 29643 ms |
| `gemma3:4b` | heldout | 50% (5/10) | 5 | 1/5 | 1/2 |  | 0 | 30796 ms |
| `qwen3-vl:2b-instruct` | tuning | 93% (14/15) | 1 | 2/4 | 14/15 |  | 0 | 2948 ms |
| `qwen3-vl:2b-instruct` | heldout | 90% (9/10) | 1 | 1/5 | 1/2 |  | 0 | 3950 ms |
| `qwen3-vl:2b-instruct` | currency |  |  |  |  | 17/18 (1 wrong) | 0 | 1750 ms |
| `qwen3-vl:4b-instruct` | tuning | 13% (2/15) | 13 | 0/4 | 14/15 |  | 0 | 3421 ms |
| `qwen3-vl:4b-instruct` | heldout | 10% (1/10) | 9 | 0/5 | 1/2 |  | 0 | 3098 ms |
| `qwen3-vl:4b-instruct` | currency |  |  |  |  | 17/18 (1 wrong) | 0 | 5908 ms |

Notes:

- The `tuning` and `heldout` rows are the first 30 tuning images and the first 17
  held-out photos, before both sets changed on 15 October 2026. The default model's
  results on the current sets are in [../results.md](../results.md) and
  [../heldout/results.md](../heldout/results.md).

- The `qwen3-vl:2b-instruct` rows were run after the JSON length limits were added
  (see the main README, section 14), as was every currency row. The tuning and held-out
  rows of the other two models were run before them, on
  14 October 2026, and have not been tuned for: their prompts are the 2B model's.
- `qwen3-vl:4b-instruct` almost never reports a hazard with these prompts, although it
  reads text and money well.
- `gemma3:4b` ran fully on the GPU but took about 30 s per image.
- Money mode was added after the gemma run, so gemma has no currency row.

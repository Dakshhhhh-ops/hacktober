Model `qwen3-vl:2b-instruct`, 30 images, run 2026-10-11 16:58.

**Missed hazards (false negatives): 1 of 15 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 30 (18 scored for hazards, 15 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 93% (14 of 15) |
| **Missed hazards** | **1** |
| False alarms | 6 (0.33 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 21% (6 of 29) |
| Hazard-free images that still got a warning | 3 of 4 |
| Text read correctly (similarity >= 80%) | 14 of 15 |
| Mean text similarity | 0.975 |
| Median model latency | 1499 ms |
| p95 model latency | 2454 ms (33 inferences) |

Missed hazards, by image:

- `trip_hazard_pavement.jpg`: uneven pavement

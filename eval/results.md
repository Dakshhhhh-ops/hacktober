Model `qwen3-vl:2b-instruct` plus the object detector, as the app uses them, 37 images, run 2026-10-15 12:39.

**Missed hazards (false negatives): 2 of 25 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 37 (25 scored for hazards, 15 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 92% (23 of 25) |
| **Missed hazards** | **2** |
| False alarms | 9 (0.36 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 18% (9 of 49) |
| Hazard-free images that still got a warning | 5 of 6 |
| Text read correctly (similarity >= 80%) | 14 of 15 |
| Mean text similarity | 0.975 |
| Median model latency | 2198 ms |
| p95 model latency | 3101 ms (40 inferences) |

Missed hazards, by image:

- `trip_hazard_pavement.jpg`: uneven pavement
- `flooded_street_dibrugarh.jpg`: pillar

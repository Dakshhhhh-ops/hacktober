Model `gemma3:4b`, 30 images, run 2026-10-14 15:20.

**Missed hazards (false negatives): 3 of 15 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 30 (18 scored for hazards, 15 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 80% (12 of 15) |
| **Missed hazards** | **3** |
| False alarms | 3 (0.17 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 15% (3 of 20) |
| Hazard-free images that still got a warning | 2 of 4 |
| Text read correctly (similarity >= 80%) | 14 of 15 |
| Mean text similarity | 0.97 |
| Median model latency | 29643 ms |
| p95 model latency | 38192 ms (33 inferences) |

Missed hazards, by image:

- `puddle_station.jpg`: wet floor
- `trip_hazard_pavement.jpg`: uneven pavement
- `wet_floor_sign_3.jpg`: bucket

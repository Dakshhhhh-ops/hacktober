Model `qwen3-vl:2b-instruct`, 30 images, run 2026-10-11 16:52.

**Missed hazards (false negatives): 6 of 15 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 30 (18 scored for hazards, 15 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 3 |
| Hazard recall | 60% (9 of 15) |
| **Missed hazards** | **6** |
| False alarms | 31 (1.72 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 58% (31 of 53) |
| Hazard-free images that still got a warning | 4 of 4 |
| Text read correctly (similarity >= 80%) | 14 of 15 |
| Mean text similarity | 0.933 |
| Median model latency | 2904 ms |
| p95 model latency | 9916 ms (33 inferences) |

Missed hazards, by image:

- `escalators.jpg`: escalator
- `plastic_barriers.jpg`: barrier
- `sidewalk_obstruction.jpg`: bicycle
- `stairs_pedway.jpg`: stairs
- `trip_hazard_pavement.jpg`: uneven pavement
- `wet_floor_sign_3.jpg`: bucket

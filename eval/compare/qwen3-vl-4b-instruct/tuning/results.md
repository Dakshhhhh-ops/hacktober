Model `qwen3-vl:4b-instruct`, 30 images, run 2026-10-14 15:02.

**Missed hazards (false negatives): 13 of 15 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 30 (18 scored for hazards, 15 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 13% (2 of 15) |
| **Missed hazards** | **13** |
| False alarms | 0 (0.0 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 0% (0 of 4) |
| Hazard-free images that still got a warning | 0 of 4 |
| Text read correctly (similarity >= 80%) | 14 of 15 |
| Mean text similarity | 0.976 |
| Median model latency | 3421 ms |
| p95 model latency | 18161 ms (33 inferences) |

Missed hazards, by image:

- `escalators.jpg`: escalator
- `plastic_barriers.jpg`: barrier
- `pothole_1.jpg`: pothole
- `pothole_2.jpg`: pothole
- `puddle_station.jpg`: wet floor
- `sidewalk_obstruction.jpg`: bicycle
- `stairs_down.jpg`: stairs
- `stairs_pedway.jpg`: stairs
- `trip_hazard_pavement.jpg`: uneven pavement
- `wet_floor_sign_1.jpg`: wet floor
- `wet_floor_sign_2.jpg`: wet floor
- `wet_floor_sign_3.jpg`: wet floor
- `wet_floor_sign_3.jpg`: bucket

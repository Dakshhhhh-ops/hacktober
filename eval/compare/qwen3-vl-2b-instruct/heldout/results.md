Model `qwen3-vl:2b-instruct`, 17 images, run 2026-10-14 15:44.

**Missed hazards (false negatives): 1 of 10 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 17 (15 scored for hazards, 2 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 90% (9 of 10) |
| **Missed hazards** | **1** |
| False alarms | 3 (0.2 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 9% (3 of 33) |
| Hazard-free images that still got a warning | 1 of 5 |
| Text read correctly (similarity >= 80%) | 1 of 2 |
| Mean text similarity | 0.768 |
| Median model latency | 3950 ms |
| p95 model latency | 8685 ms (17 inferences) |

Missed hazards, by image:

- `potholed_road_kolkata.jpg`: pothole

With only 17 images these numbers describe this image set. They are not a statistically meaningful estimate of real-world performance.

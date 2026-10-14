Model `gemma3:4b`, 17 images, run 2026-10-14 15:29.

**Missed hazards (false negatives): 5 of 10 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 17 (15 scored for hazards, 2 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 50% (5 of 10) |
| **Missed hazards** | **5** |
| False alarms | 1 (0.07 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 6% (1 of 17) |
| Hazard-free images that still got a warning | 1 of 5 |
| Text read correctly (similarity >= 80%) | 1 of 2 |
| Mean text similarity | 0.839 |
| Median model latency | 30796 ms |
| p95 model latency | 32134 ms (17 inferences) |

Missed hazards, by image:

- `potholed_road_kolkata.jpg`: pothole
- `potholes_bihar.jpg`: puddle
- `cow_street_delhi.jpg`: cow
- `cow_street_madurai.jpg`: cow
- `drain_unbuilt.jpg`: trench

With only 17 images these numbers describe this image set. They are not a statistically meaningful estimate of real-world performance.

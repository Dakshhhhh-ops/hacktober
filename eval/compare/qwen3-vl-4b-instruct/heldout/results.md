Model `qwen3-vl:4b-instruct`, 17 images, run 2026-10-14 15:03.

**Missed hazards (false negatives): 9 of 10 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 17 (15 scored for hazards, 2 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 10% (1 of 10) |
| **Missed hazards** | **9** |
| False alarms | 0 (0.0 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 0% (0 of 1) |
| Hazard-free images that still got a warning | 0 of 5 |
| Text read correctly (similarity >= 80%) | 1 of 2 |
| Mean text similarity | 0.81 |
| Median model latency | 3098 ms |
| p95 model latency | 4675 ms (17 inferences) |

Missed hazards, by image:

- `broken_road_delhi.jpg`: hole
- `potholed_road_kolkata.jpg`: pothole
- `potholes_bihar.jpg`: puddle
- `cow_street_delhi.jpg`: cow
- `cow_street_madurai.jpg`: cow
- `cows_road_delhi.jpg`: cow
- `autos_ahmedabad.jpg`: auto rickshaw
- `manhole_delhi.jpg`: open drain
- `platform_new_delhi.jpg`: railway track

With only 17 images these numbers describe this image set. They are not a statistically meaningful estimate of real-world performance.

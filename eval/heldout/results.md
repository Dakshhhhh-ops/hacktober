Model `qwen3-vl:2b-instruct`, 39 images, run 2026-10-15 11:13.

**Missed hazards (false negatives): 13 of 42 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 39 (37 scored for hazards, 2 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 69% (29 of 42) |
| **Missed hazards** | **13** |
| False alarms | 8 (0.22 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 11% (8 of 73) |
| Hazard-free images that still got a warning | 4 of 10 |
| Text read correctly (similarity >= 80%) | 2 of 2 |
| Mean text similarity | 0.941 |
| Median model latency | 2703 ms |
| p95 model latency | 3277 ms (39 inferences) |

Missed hazards, by image:

- `potholed_road_kolkata.jpg`: pothole
- `potholes_puddle_auto.jpg`: auto rickshaw
- `pothole_bengaluru.jpg`: pothole
- `flooded_handpump_chennai.jpg`: hand pump
- `flooded_street_kanchipuram.jpg`: person
- `flooded_street_dibrugarh.jpg`: pillar
- `flooded_street_mumbai.jpg`: vehicle
- `manhole_charminar.jpg`: water
- `cow_footpath_mumbai.jpg`: umbrella
- `blocked_footpath_mumbai.jpg`: hammock
- `cows_dog_road_delhi.jpg`: motorcycle
- `ghat_steps_varanasi.jpg`: person
- `station_stairs_ernakulam.jpg`: person

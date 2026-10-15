Model `qwen3-vl:2b-instruct`, 37 images, run 2026-10-15 11:47.

**Missed hazards (false negatives): 6 of 25 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 37 (25 scored for hazards, 15 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 76% (19 of 25) |
| **Missed hazards** | **6** |
| False alarms | 5 (0.2 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 14% (5 of 37) |
| Hazard-free images that still got a warning | 4 of 6 |
| Text read correctly (similarity >= 80%) | 14 of 15 |
| Mean text similarity | 0.975 |
| Median model latency | 1960 ms |
| p95 model latency | 2872 ms (40 inferences) |

Missed hazards, by image:

- `trip_hazard_pavement.jpg`: uneven pavement
- `flooded_handpump_chennai.jpg`: hand pump
- `flooded_street_dibrugarh.jpg`: pillar
- `flooded_street_mumbai.jpg`: vehicle
- `ghat_steps_varanasi.jpg`: person
- `station_stairs_ernakulam.jpg`: person

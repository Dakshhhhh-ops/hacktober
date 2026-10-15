Model `qwen3-vl:2b-instruct` plus the object detector, as the app uses them, 52 images, run 2026-10-15 12:41.

**Missed hazards (false negatives): 11 of 60 labelled hazards.**

| Metric | Value |
| --- | --- |
| Images evaluated | 52 (50 scored for hazards, 2 for reading) |
| Failed inferences | 0 |
| Plain-text fallbacks (no validated JSON) | 0 |
| Hazard recall | 82% (49 of 60) |
| **Missed hazards** | **11** |
| False alarms | 11 (0.22 per image) |
| False-alarm rate (false alarms / all hazards the model reported) | 10% (11 of 115) |
| Hazard-free images that still got a warning | 3 of 12 |
| Text read correctly (similarity >= 80%) | 2 of 2 |
| Mean text similarity | 0.941 |
| Median model latency | 2806 ms |
| p95 model latency | 3354 ms (52 inferences) |

Missed hazards, by image:

- `potholed_road_kolkata.jpg`: pothole
- `potholes_puddle_auto.jpg`: auto rickshaw
- `pothole_bengaluru.jpg`: pothole
- `manhole_charminar.jpg`: water
- `cow_footpath_mumbai.jpg`: umbrella
- `blocked_footpath_mumbai.jpg`: hammock
- `cows_dog_road_delhi.jpg`: motorcycle
- `flooded_cars_hyderabad.jpg`: wire
- `temple_steps_palitana.jpg`: pole
- `ghat_people_varanasi.jpg`: water
- `ghat_rituals_varanasi.jpg`: lamps

"""What gets spoken, in what order, and what is suppressed."""
import json
import unittest

from drishti.schema import FindResult, Scene
from drishti.speech import RepeatFilter, build_speech

SCENE = Scene.model_validate_json(json.dumps({
    "hazards": [
        {"what": "parked scooter", "where": "right", "distance": "far"},
        {"what": "stairs", "where": "ahead", "distance": "near"},
    ],
    "objects": [{"what": "bench", "where": "left"}],
    "text": ["Platform 2", " "],
    "summary": "A corridor with stairs going down.",
}))
EMPTY = Scene.from_summary("")


class BuildSpeechTests(unittest.TestCase):
    def test_hazards_are_spoken_nearest_first(self):
        hazards, _ = build_speech(SCENE, "surroundings")
        self.assertEqual(hazards, [
            "Careful: stairs ahead, near.",
            "Careful: parked scooter on the right, far.",
        ])

    def test_surroundings_speaks_the_summary_but_not_objects_or_text(self):
        _, rest = build_speech(SCENE, "surroundings")
        self.assertEqual(rest, ["A corridor with stairs going down."])

    def test_read_speaks_the_text_and_keeps_hazards(self):
        hazards, rest = build_speech(SCENE, "read")
        self.assertEqual(len(hazards), 2)
        self.assertEqual(rest, ["Platform 2"])

    def test_read_with_no_text_says_so(self):
        _, rest = build_speech(EMPTY, "read")
        self.assertEqual(rest, ["No readable text."])

    def test_find_found_gives_the_location(self):
        found = FindResult(status="found", where="on the desk, to the left.")
        _, rest = build_speech(SCENE, "find", "en", "keys", found)
        self.assertEqual(rest, ["Found keys: on the desk, to the left."])

    def test_find_not_found_and_uncertain_are_different_sentences(self):
        _, missing = build_speech(EMPTY, "find", "en", "keys", FindResult(status="not_found"))
        _, unsure = build_speech(EMPTY, "find", "en", "keys", FindResult(status="uncertain"))
        self.assertEqual(missing, ["I cannot see keys."])
        self.assertEqual(unsure, ["I am not sure whether keys is here."])

    def test_find_still_speaks_hazards_first(self):
        hazards, _ = build_speech(SCENE, "find", "en", "keys", FindResult(status="not_found"))
        self.assertEqual(hazards[0], "Careful: stairs ahead, near.")

    def test_a_fallback_is_marked_as_rough(self):
        scene = Scene.from_summary("A desk with a laptop.")
        _, rest = build_speech(scene, "find", "en", "keys", None, fallback=True)
        self.assertEqual(rest, ["Rough description: A desk with a laptop."])

    def test_a_long_summary_is_cut_short(self):
        scene = Scene.from_summary(" ".join(["word"] * 60))
        _, rest = build_speech(scene, "surroundings")
        self.assertEqual(len(rest[0].split()), 25)

    def test_hindi_uses_hindi_direction_and_distance_words(self):
        hazards, _ = build_speech(SCENE, "surroundings", "hi")
        self.assertEqual(hazards[0], "सावधान: सामने stairs, पास।")

    def test_an_empty_scene_never_claims_it_is_safe(self):
        hazards, rest = build_speech(EMPTY, "surroundings")
        self.assertEqual((hazards, rest), ([], ["Nothing clear to report."]))


class RepeatFilterTests(unittest.TestCase):
    def test_the_same_hazard_is_suppressed_inside_the_window(self):
        now = [0.0]
        repeats = RepeatFilter(20, clock=lambda: now[0])
        stairs = "Careful: stairs ahead, near."
        car = "Careful: car on the left, mid distance."
        self.assertEqual(repeats.fresh([stairs]), [stairs])
        now[0] = 10
        self.assertEqual(repeats.fresh([stairs.lower(), car]), [car])
        now[0] = 25
        self.assertEqual(repeats.fresh([stairs]), [stairs])

    def test_a_manual_description_also_counts_as_spoken(self):
        now = [0.0]
        repeats = RepeatFilter(20, clock=lambda: now[0])
        repeats.remember(["Careful: stairs ahead, near."])
        now[0] = 5
        self.assertEqual(repeats.fresh(["Careful: stairs ahead, near."]), [])


if __name__ == "__main__":
    unittest.main()

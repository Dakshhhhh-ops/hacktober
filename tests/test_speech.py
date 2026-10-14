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

    def test_a_hazard_listed_twice_is_spoken_once(self):
        twice = Scene.model_validate_json(json.dumps({
            "hazards": [{"what": "railing", "where": "left", "distance": "near"}] * 2,
            "objects": [], "text": [], "summary": "",
        }))
        hazards, _ = build_speech(twice, "surroundings")
        self.assertEqual(hazards, ["Careful: railing on the left, near."])

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

    def test_hindi_translates_the_hazard_direction_and_distance(self):
        hazards, _ = build_speech(SCENE, "surroundings", "hi")
        self.assertEqual(hazards[0], "सावधान: सामने सीढ़ियाँ, पास।")
        self.assertEqual(hazards[1], "सावधान: दाईं ओर स्कूटर, दूर।")

    def test_hindi_summary_is_built_from_known_objects(self):
        _, rest = build_speech(SCENE, "surroundings", "hi")
        self.assertEqual(rest, ["दिख रहा है: बेंच।"])

    def test_hindi_keeps_an_unknown_word_in_english_instead_of_guessing(self):
        odd = Scene.model_validate_json(json.dumps({
            "hazards": [{"what": "gyroscope", "where": "left", "distance": "mid"}],
            "objects": [], "text": [], "summary": "A lab bench.",
        }))
        hazards, rest = build_speech(odd, "surroundings", "hi")
        self.assertEqual(hazards, ["सावधान: बाईं ओर gyroscope, थोड़ी दूर।"])
        self.assertEqual(rest, ["A lab bench."])

    def test_hindi_find_translates_the_location(self):
        found = FindResult(status="found", where="on the table, to the left")
        _, rest = build_speech(SCENE, "find", "hi", "water bottle", found)
        self.assertEqual(rest, ["बोतल दिख रहा है: मेज़ पर, बाईं ओर।"])

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


class MoneySpeechTests(unittest.TestCase):
    def money(self, *items):
        from drishti.schema import Money
        return [Money(value=v, kind=k) for v, k in items]

    def test_one_note(self):
        _, rest = build_speech(EMPTY, "money", money=self.money((500, "note")))
        self.assertEqual(rest, ["500 rupee note."])

    def test_several_are_grouped_largest_first_and_totalled_here(self):
        items = self.money((100, "note"), (500, "note"), (100, "note"), (10, "coin"))
        _, rest = build_speech(EMPTY, "money", money=items)
        self.assertEqual(rest, ["500 rupee note.", "2 notes of 100 rupees.", "10 rupee coin.",
                                "Total 710 rupees."])

    def test_hindi(self):
        _, rest = build_speech(EMPTY, "money", "hi", money=self.money((200, "note"), (200, "note")))
        self.assertEqual(rest, ["200 रुपये के 2 नोट।", "कुल 400 रुपये।"])

    def test_no_money_says_so(self):
        _, rest = build_speech(EMPTY, "money", money=[])
        self.assertEqual(rest, ["I cannot see any Indian money."])


class BlurNoteTests(unittest.TestCase):
    def test_a_blurred_frame_says_so_after_the_warnings_and_before_the_rest(self):
        hazards, rest = build_speech(SCENE, "surroundings", blurry=True)
        self.assertEqual(hazards[0], "Careful: stairs ahead, near.")
        self.assertEqual(rest[0], "The picture is blurred, so this may be wrong. Hold the camera still.")
        self.assertEqual(rest[1], "A corridor with stairs going down.")

    def test_hindi(self):
        _, rest = build_speech(SCENE, "surroundings", "hi", blurry=True)
        self.assertTrue(rest[0].startswith("तस्वीर धुँधली है"))

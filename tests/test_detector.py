"""Object detector: decoding, what becomes a warning, and walk mode. The network is not run."""
import base64
import unittest
from unittest import mock

from drishti import detector, server, tts
from drishti.detector import Detection
from drishti.schema import Hazard

try:
    import cv2  # noqa: F401
    import numpy as np
except ImportError:  # the CI unit tests do not install OpenCV
    np = None


def box(label, x1, y1, x2, y2, score=0.9):
    return Detection(label, score, (x1, y1, x2, y2))


class PlaceTests(unittest.TestCase):
    def test_direction_comes_from_the_middle_of_the_box(self):
        self.assertEqual(box("car", 0.0, 0.4, 0.2, 0.6).where, "left")
        self.assertEqual(box("car", 0.4, 0.4, 0.6, 0.6).where, "ahead")
        self.assertEqual(box("car", 0.8, 0.4, 1.0, 0.6).where, "right")

    def test_distance_is_a_rough_guess_from_size(self):
        self.assertEqual(box("car", 0.2, 0.2, 0.8, 0.9).distance, "near")
        self.assertEqual(box("car", 0.45, 0.4, 0.55, 0.65).distance, "mid")
        self.assertEqual(box("car", 0.48, 0.45, 0.52, 0.5).distance, "far")


class HazardTests(unittest.TestCase):
    def test_general_words_are_spoken(self):
        found = [box("truck", 0.4, 0.2, 0.6, 0.9), box("dog", 0.0, 0.2, 0.3, 0.9)]
        self.assertEqual({h.what for h in detector.hazards(found)}, {"vehicle", "animal"})

    def test_a_crowd_is_one_warning_per_direction_nearest_first(self):
        crowd = [box("person", 0.45, 0.4, 0.55, 0.65), box("person", 0.4, 0.1, 0.6, 0.9),
                 box("person", 0.42, 0.4, 0.5, 0.6)]
        self.assertEqual(detector.hazards(crowd),
                         [Hazard(what="person", where="ahead", distance="near")])

    def test_far_things_furniture_and_trains_are_left_out(self):
        found = [box("person", 0.48, 0.45, 0.52, 0.5), box("chair", 0.3, 0.2, 0.7, 0.9),
                 box("train", 0.1, 0.1, 0.9, 0.9)]
        self.assertEqual(detector.hazards(found), [])
        self.assertEqual(len(detector.hazards(found[:1], include_far=True)), 1)

    def test_walk_mode_warns_about_near_things_and_mid_distance_ahead_only(self):
        found = [box("car", 0.0, 0.3, 0.3, 0.6),      # mid, left: not said
                 box("car", 0.4, 0.4, 0.6, 0.65),     # mid, ahead: said
                 box("dog", 0.7, 0.1, 1.0, 0.95)]     # near, right: said
        self.assertEqual([(h.what, h.where, h.distance) for h in detector.walk_warnings(found)],
                         [("animal", "right", "near"), ("vehicle", "ahead", "mid")])

    def test_what_the_vision_model_already_said_is_not_repeated(self):
        model = [Hazard(what="stray cow", where="ahead", distance="near")]
        detected = [Hazard(what="animal", where="ahead", distance="near"),
                    Hazard(what="vehicle", where="left", distance="mid")]
        self.assertEqual([h.what for h in detector.missing_from(model, detected)], ["vehicle"])


@unittest.skipIf(np is None, "OpenCV and numpy are not installed")
class DecodeTests(unittest.TestCase):
    def test_one_confident_cell_becomes_one_detection_in_frame_fractions(self):
        raw = np.zeros((3549, 85), np.float32)
        # Cell (x=26, y=26) at stride 8 has its centre at 208 px. A 100 x 100 px box there,
        # "cow" (class 19) with objectness 0.9 and class score 0.9.
        cell = 26 * 52 + 26
        raw[cell, :4] = [0, 0, np.log(100 / 8), np.log(100 / 8)]
        raw[cell, 4] = 0.9
        raw[cell, 5 + 19] = 0.9
        found = detector.decode(raw, ratio=1.0, width=416, height=416)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].label, "cow")
        self.assertAlmostEqual(found[0].score, 0.81, places=2)
        for value, expected in zip(found[0].box, (158 / 416, 158 / 416, 258 / 416, 258 / 416)):
            self.assertAlmostEqual(value, expected, places=3)

    def test_nothing_confident_means_nothing_found(self):
        self.assertEqual(detector.decode(np.zeros((3549, 85), np.float32), 1.0, 416, 416), [])


class SpeechCacheTests(unittest.TestCase):
    def setUp(self):
        tts._cache.clear()

    def test_a_short_sentence_is_synthesised_once(self):
        with mock.patch.object(tts, "_synthesize", return_value=b"RIFF") as synth:
            tts.synthesize("Careful: vehicle ahead, near.", "en")
            tts.synthesize("Careful: vehicle ahead, near.", "en")
        self.assertEqual(synth.call_count, 1)

    def test_long_text_and_failures_are_not_kept(self):
        with mock.patch.object(tts, "_synthesize", side_effect=[b"a", b"b", None, None]) as synth:
            tts.synthesize("x" * 500, "en")
            tts.synthesize("x" * 500, "en")
            tts.synthesize("short", "en")
            tts.synthesize("short", "en")
        self.assertEqual(synth.call_count, 4)


class DetectEndpointTests(unittest.TestCase):
    JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()

    def setUp(self):
        server.walk_repeats = server.RepeatFilter(6)

    def call(self, found):
        with mock.patch.object(detector, "available", return_value=True), \
                mock.patch.object(detector, "detect", return_value=found):
            return server.detect(server.DetectRequest(image=self.JPEG))

    def test_close_things_are_warned_about_once_within_a_few_seconds(self):
        cow = [box("cow", 0.3, 0.1, 0.7, 0.95)]
        first = self.call(cow)
        self.assertEqual(first["speech"]["hazards"], ["Careful: animal ahead, near."])
        self.assertEqual(self.call(cow)["speech"]["hazards"], [])
        self.assertEqual(len(self.call(cow)["hazards"]), 1)  # still shown, just not spoken

    def test_hindi(self):
        with mock.patch.object(detector, "available", return_value=True), \
                mock.patch.object(detector, "detect", return_value=[box("cow", 0.3, 0.1, 0.7, 0.95)]):
            response = server.detect(server.DetectRequest(image=self.JPEG, lang="hi"))
        self.assertEqual(response["speech"]["hazards"], ["सावधान: सामने जानवर, पास।"])

    def test_broken_base64_is_refused_not_a_crash(self):
        with mock.patch.object(detector, "available", return_value=True):
            response = server.detect(server.DetectRequest(image="/9j/4AAQSkZJRgABAQAAAA="[:-2] + "x"))
        self.assertEqual(response.status_code, 400)

    def test_without_the_model_file_walk_mode_says_it_is_unavailable(self):
        with mock.patch.object(detector, "available", return_value=False):
            response = server.detect(server.DetectRequest(image=self.JPEG))
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()


class FindTests(unittest.TestCase):
    def test_what_a_person_asks_for_maps_to_detector_classes(self):
        self.assertEqual(detector.find_labels("my water bottle"), ("bottle",))
        self.assertEqual(detector.find_labels("the cups"), ("cup",))
        self.assertEqual(detector.find_labels("mobile phone"), ("cell phone",))
        self.assertIn("backpack", detector.find_labels("laptop bag"))  # a bag, not a laptop

    def test_things_the_detector_does_not_know_go_to_the_vision_model(self):
        for target in ("keys", "door", "medicine", "spectacles"):
            self.assertIsNone(detector.find_labels(target), target)

    def test_the_most_confident_match_is_chosen_and_weak_ones_ignored(self):
        found = [box("bottle", 0.0, 0.4, 0.1, 0.6, score=0.5), box("bottle", 0.8, 0.4, 1.0, 0.6, score=0.7),
                 box("cup", 0.4, 0.4, 0.6, 0.6, score=0.95), box("bottle", 0.4, 0.4, 0.6, 0.6, score=0.2)]
        best = detector.locate(found, ("bottle",))
        self.assertEqual((best.where, best.score), ("right", 0.7))
        self.assertIsNone(detector.locate(found[3:], ("bottle",)))


class LocateEndpointTests(unittest.TestCase):
    JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()

    def call(self, target, found, lang="en"):
        with mock.patch.object(detector, "available", return_value=True), \
                mock.patch.object(detector, "detect", return_value=found):
            return server.locate(server.LocateRequest(image=self.JPEG, target=target, lang=lang))

    def test_found_says_where(self):
        answer = self.call("my water bottle", [box("bottle", 0.0, 0.1, 0.3, 0.95)])
        self.assertEqual((answer["known"], answer["found"]), (True, True))
        self.assertEqual(answer["sentence"], "Water bottle on the left, near.")

    def test_hindi(self):
        answer = self.call("bottle", [box("bottle", 0.45, 0.4, 0.55, 0.65)], "hi")
        self.assertEqual(answer["sentence"], "बोतल सामने, थोड़ी दूर।")

    def test_not_in_view(self):
        self.assertEqual(self.call("phone", [box("cup", 0.4, 0.4, 0.6, 0.6)])["found"], False)

    def test_unknown_objects_are_left_to_the_vision_model(self):
        self.assertEqual(self.call("keys", []), {"known": False, "found": False})

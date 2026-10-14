"""The evaluation's matching rules and metrics, with a fake pipeline."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from drishti import vlm
from drishti.schema import Scene

_spec = importlib.util.spec_from_file_location(
    "run_eval", Path(__file__).resolve().parent.parent / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_eval)


def scene(hazards=(), text=()):
    return Scene.model_validate_json(json.dumps({
        "hazards": [{"what": h, "where": "ahead", "distance": "near"} for h in hazards],
        "objects": [], "text": list(text), "summary": "",
    }))


def result(hazards=(), text=(), ms=1000):
    return vlm.Result(scene=scene(hazards, text), find_result=None, status="ok", retries=0,
                      inference_ms=ms, request_id="x", model="test")


class MatchingTests(unittest.TestCase):
    def test_labels_with_synonyms_are_parsed(self):
        self.assertEqual(run_eval.parse_hazard_labels("stairs|steps; wet floor"),
                         [["stairs", "steps"], ["wet floor"]])
        self.assertEqual(run_eval.parse_hazard_labels(""), [])

    def test_a_hazard_matches_by_containment_plural_or_synonym(self):
        self.assertTrue(run_eval.phrases_match("stairs", "Stairs going down."))
        self.assertTrue(run_eval.phrases_match("step", "steps"))
        detected, missed, alarms = run_eval.match_hazards([["stairs", "steps"]], ["concrete steps"])
        self.assertEqual((detected, missed, alarms), (["stairs"], [], []))

    def test_missed_hazards_and_false_alarms_are_separated(self):
        detected, missed, alarms = run_eval.match_hazards(
            [["stairs"], ["wet floor"]], ["stairs ahead", "parked car"])
        self.assertEqual((detected, missed, alarms), (["stairs"], ["wet floor"], ["parked car"]))

    def test_one_prediction_cannot_satisfy_two_labels(self):
        _, missed, _ = run_eval.match_hazards([["chair"], ["chair"]], ["chair"])
        self.assertEqual(missed, ["chair"])

    def test_an_optional_label_is_neither_a_miss_nor_a_false_alarm(self):
        labels = run_eval.parse_hazard_labels("open manhole|manhole;?traffic cone|cone;?car")
        self.assertEqual(run_eval.match_hazards(labels, ["open manhole", "orange cone"]),
                         (["open manhole"], [], []))
        self.assertEqual(run_eval.match_hazards(labels, ["open manhole"]),
                         (["open manhole"], [], []))
        self.assertEqual(run_eval.match_hazards(labels, ["cone", "dog"]),
                         ([], ["open manhole"], ["dog"]))

    def test_text_similarity_ignores_case_and_punctuation(self):
        self.assertEqual(run_eval.text_similarity("CAUTION: Wet Floor!", ["caution", "wet floor"]), 1.0)
        self.assertLess(run_eval.text_similarity("Paracetamol 500 mg", ["Platform 2"]), 0.5)

    def test_percentile_uses_nearest_rank(self):
        self.assertEqual(run_eval.percentile([100, 200, 300, 400], 95), 400)
        self.assertEqual(run_eval.percentile([100], 95), 100)


class EvaluateTests(unittest.TestCase):
    def run_eval_with(self, rows, answers):
        calls = iter(answers)

        def describe(image_b64, mode, lang):
            answer = next(calls)
            if isinstance(answer, Exception):
                raise answer
            return answer

        with tempfile.TemporaryDirectory() as folder:
            for row in rows:
                (Path(folder) / row["image"]).write_bytes(b"\xff\xd8\xff")
            results = run_eval.evaluate(rows, Path(folder), describe=describe)
        return results, run_eval.summarise(results)

    def test_metrics_on_a_small_set(self):
        rows = [
            {"image": "a.jpg", "hazards_true": "stairs|steps", "text_true": ""},
            {"image": "b.jpg", "hazards_true": "wet floor", "text_true": "CAUTION"},
            {"image": "c.jpg", "hazards_true": "", "text_true": ""},
        ]
        answers = [
            result(["steps going down"], ms=1000),          # a: detected
            result([], ms=2000), result(text=["CAUTION"], ms=3000),  # b: missed, text right
            result(["dog"], ms=4000),                        # c: false alarm
        ]
        results, s = self.run_eval_with(rows, answers)
        self.assertEqual((s["hazards_detected"], s["hazards_missed"], s["false_alarms"]), (1, 1, 1))
        self.assertEqual(s["hazard_recall"], 0.5)
        self.assertEqual(s["false_alarm_rate"], 0.5)          # 1 of the 2 hazards it reported
        self.assertEqual(s["false_alarms_per_image"], 0.33)
        self.assertEqual((s["hazard_free_images"], s["hazard_free_images_with_alarm"]), (1, 1))
        self.assertEqual((s["text_images"], s["text_read_correctly"]), (1, 1))
        self.assertEqual((s["latency_median_ms"], s["latency_p95_ms"]), (2500, 4000))
        markdown = run_eval.to_markdown(s, results, "test")
        self.assertIn("**Missed hazards (false negatives): 1 of 2 labelled hazards.**", markdown)
        self.assertIn("`b.jpg`: wet floor", markdown)
        self.assertIn("not a statistically meaningful", markdown)

    def test_a_reading_only_image_is_not_scored_for_hazards(self):
        rows = [{"image": "sign.png", "hazards_true": "n/a", "text_true": "EXIT"}]
        results, s = self.run_eval_with(rows, [result(text=["EXIT"], ms=900)])
        self.assertEqual((s["images"], s["images_scored_for_hazards"]), (1, 0))
        self.assertEqual((s["text_read_correctly"], s["false_alarms"]), (1, 0))
        self.assertIsNone(s["false_alarms_per_image"])
        self.assertEqual(s["inferences_timed"], 1)

    def test_a_failed_inference_is_counted_not_hidden(self):
        rows = [{"image": "a.jpg", "hazards_true": "stairs", "text_true": ""}]
        _, s = self.run_eval_with(rows, [vlm.VLMError("Ollama is down")])
        self.assertEqual((s["images"], s["failed_inferences"]), (1, 1))
        self.assertIsNone(s["hazard_recall"])

    def test_a_missing_image_is_a_failure(self):
        results = run_eval.evaluate(
            [{"image": "nope.jpg", "hazards_true": "", "text_true": ""}], Path("."),
            describe=lambda *a: result())
        self.assertTrue(results[0]["failed"])


if __name__ == "__main__":
    unittest.main()


class MoneyEvalTests(unittest.TestCase):
    run_eval_with = EvaluateTests.run_eval_with

    def money(self, *values):
        from drishti.schema import Money
        found = result()
        found.money = [Money(value=v, kind="note") for v in values]
        return found

    def test_money_is_scored_by_denomination_and_a_wrong_value_is_counted(self):
        rows = [{"image": f"{n}.jpg", "hazards_true": "n/a", "text_true": "", "money_true": truth}
                for n, truth in (("a", "500"), ("b", "100;2000"), ("c", "50"), ("d", "10"))]
        answers = [self.money(500), self.money(100, 100, 2000), self.money(500), self.money()]
        _, summary = self.run_eval_with(rows, answers)
        self.assertEqual((summary["money_images"], summary["money_correct"]), (4, 2))
        self.assertEqual(summary["money_wrong_value"], 1)
        self.assertEqual(summary["money_nothing_seen"], 1)

"""JSON validation, retry and fallback, tested with a fake model (no Ollama needed)."""
import json
import unittest

from drishti import vlm

SCENE = {
    "hazards": [{"what": "stairs", "where": "ahead", "distance": "near"}],
    "objects": [{"what": "door", "where": "left"}],
    "text": ["EXIT"],
    "summary": "A staircase going down.",
}
GOOD = json.dumps(SCENE)
IMAGE = "aW1hZ2U="


def fake_post(*replies):
    """A stand-in for Ollama that returns the given replies in order."""
    queue = list(replies)
    calls = []

    def post(payload):
        calls.append(payload)
        reply = queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    post.calls = calls
    return post


class DescribeTests(unittest.TestCase):
    def describe(self, post, mode="surroundings", target=""):
        return vlm.describe(IMAGE, mode, "en", target, post=post, log=False)

    def test_valid_json_is_used_directly(self):
        post = fake_post(GOOD)
        result = self.describe(post)
        self.assertEqual((result.status, result.retries), ("ok", 0))
        self.assertEqual(result.scene.hazards[0].what, "stairs")
        self.assertEqual(len(post.calls), 1)
        self.assertIn("format", post.calls[0])

    def test_json_inside_a_code_fence_is_accepted(self):
        self.assertEqual(self.describe(fake_post(f"```json\n{GOOD}\n```")).status, "ok")

    def test_invalid_json_is_retried_once_with_a_correction(self):
        post = fake_post("I see some stairs.", GOOD)
        result = self.describe(post)
        self.assertEqual((result.status, result.retries), ("ok", 1))
        self.assertEqual(post.calls[1]["messages"][-2]["content"], "I see some stairs.")
        self.assertEqual([a["parse_outcome"] for a in result.attempts], ["invalid_json", "valid"])

    def test_an_enum_value_outside_the_schema_is_rejected(self):
        bad = GOOD.replace('"ahead"', '"in front"')
        result = self.describe(fake_post(bad, GOOD))
        self.assertEqual(result.attempts[0]["parse_outcome"], "schema_error")

    def test_a_wrong_field_type_is_rejected(self):
        bad = json.dumps(dict(SCENE, summary=42))
        result = self.describe(fake_post(bad, GOOD))
        self.assertEqual(result.attempts[0]["parse_outcome"], "schema_error")
        bad_list = json.dumps(dict(SCENE, text="EXIT"))
        self.assertEqual(self.describe(fake_post(bad_list, GOOD)).retries, 1)

    def test_two_failures_fall_back_to_plain_text_without_inventing_hazards(self):
        post = fake_post("nope", "{still not json", "  Stairs ahead,\n going down. ")
        result = self.describe(post)
        self.assertEqual(result.status, "fallback")
        self.assertEqual(result.scene.summary, "Stairs ahead, going down.")
        self.assertEqual(result.scene.hazards, [])
        self.assertNotIn("format", post.calls[2])
        self.assertEqual(result.attempts[-1]["parse_outcome"], "plain_text")

    def test_an_empty_fallback_is_an_error_not_a_made_up_answer(self):
        with self.assertRaises(vlm.VLMError):
            self.describe(fake_post("nope", "nope", "   "))

    def test_an_unreachable_model_raises_with_a_fix(self):
        down = vlm.VLMError("Could not reach Ollama.", fix="Start Ollama.")
        with self.assertRaises(vlm.VLMError) as caught:
            self.describe(fake_post(down))
        self.assertEqual(caught.exception.fix, "Start Ollama.")

    def test_find_mode_returns_an_explicit_find_result(self):
        reply = json.dumps(dict(SCENE, find_result={"status": "found", "where": "on the desk"}))
        post = fake_post(reply)
        result = self.describe(post, "find", "my keys")
        self.assertEqual(result.find_result.status, "found")
        self.assertIn("my keys", post.calls[0]["messages"][1]["content"])
        self.assertIn("find_result", post.calls[0]["format"]["properties"])

    def test_find_mode_rejects_a_reply_without_find_result(self):
        result = self.describe(fake_post(GOOD, "nope", "A desk."), "find", "keys")
        self.assertEqual(result.status, "fallback")
        self.assertIsNone(result.find_result)

    def test_hindi_prompt_asks_for_devanagari(self):
        post = fake_post(GOOD)
        vlm.describe(IMAGE, "surroundings", "hi", post=post, log=False)
        self.assertIn("Devanagari", post.calls[0]["messages"][1]["content"])

    def test_inference_time_is_the_sum_of_all_attempts(self):
        result = self.describe(fake_post("nope", GOOD))
        self.assertEqual(result.inference_ms, sum(a["inference_ms"] for a in result.attempts))


if __name__ == "__main__":
    unittest.main()

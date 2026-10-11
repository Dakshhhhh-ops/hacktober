"""API behaviour, calling the endpoint functions directly with the model and TTS mocked."""
import base64
import json
import unittest
from unittest import mock

from drishti import server, vlm
from drishti.schema import FindResult, Scene

JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"0" * 64).decode()
SCENE = Scene.model_validate_json(json.dumps({
    "hazards": [{"what": "stairs", "where": "ahead", "distance": "near"}],
    "objects": [], "text": ["EXIT"], "summary": "A staircase.",
}))


def result(status="ok", find_result=None, scene=SCENE):
    return vlm.Result(scene=scene, find_result=find_result, status=status, retries=0,
                      inference_ms=1200, request_id="abc123", model="test-model")


def body(response):
    return json.loads(response.body)


class DescribeEndpointTests(unittest.TestCase):
    def setUp(self):
        server.repeats = server.RepeatFilter(20)

    def call(self, **fields):
        return server.describe(server.DescribeRequest(image=JPEG, **fields))

    def test_success_returns_the_envelope_with_hazards_first(self):
        with mock.patch.object(vlm, "describe", return_value=result()):
            response = self.call()
        self.assertEqual(response.status, "ok")
        self.assertEqual(response.speech.hazards, ["Careful: stairs ahead, near."])
        self.assertEqual(response.speech.rest, ["A staircase."])
        self.assertEqual((response.inference_ms, response.request_id), (1200, "abc123"))

    def test_a_data_url_prefix_is_accepted(self):
        with mock.patch.object(vlm, "describe", return_value=result()) as described:
            server.describe(server.DescribeRequest(image="data:image/jpeg;base64," + JPEG))
        self.assertEqual(described.call_args.args[0], JPEG)

    def test_model_unavailable_gives_503_with_a_fix(self):
        error = vlm.VLMError("Could not reach Ollama.", fix="Start Ollama.")
        with mock.patch.object(vlm, "describe", side_effect=error):
            response = self.call()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(body(response)["status"], "error")
        self.assertEqual(body(response)["error"], {"message": "Could not reach Ollama.", "fix": "Start Ollama."})
        self.assertIsNone(body(response)["scene"])

    def test_a_file_that_is_not_an_image_is_rejected(self):
        not_image = base64.b64encode(b"MZ this is an exe" + b"0" * 32).decode()
        with mock.patch.object(vlm, "describe") as described:
            response = server.describe(server.DescribeRequest(image=not_image))
        self.assertEqual(response.status_code, 400)
        described.assert_not_called()

    def test_an_oversized_image_is_rejected(self):
        with mock.patch.object(server.config, "MAX_IMAGE_BYTES", 16):
            response = self.call()
        self.assertEqual(response.status_code, 400)

    def test_find_without_a_target_is_rejected(self):
        self.assertEqual(self.call(mode="find").status_code, 400)

    def test_find_result_is_passed_through_and_spoken(self):
        found = result(find_result=FindResult(status="found", where="on the desk"))
        with mock.patch.object(vlm, "describe", return_value=found):
            response = self.call(mode="find", target="keys")
        self.assertEqual(response.find_result.status, "found")
        self.assertEqual(response.speech.rest, ["Found keys: on the desk."])

    def test_fallback_is_marked_in_status_and_speech(self):
        rough = result(status="fallback", scene=Scene.from_summary("A desk."))
        with mock.patch.object(vlm, "describe", return_value=rough):
            response = self.call()
        self.assertEqual(response.status, "fallback")
        self.assertEqual(response.speech.rest, ["Rough description: A desk."])

    def test_automatic_frames_do_not_repeat_a_recent_hazard(self):
        with mock.patch.object(vlm, "describe", return_value=result()):
            first = self.call(auto=True)
            second = self.call(auto=True)
            manual = self.call(auto=False)
        self.assertEqual(first.speech.hazards, ["Careful: stairs ahead, near."])
        self.assertEqual((second.speech.hazards, second.speech.rest), ([], []))
        # A manual request always speaks everything.
        self.assertEqual(manual.speech.hazards, ["Careful: stairs ahead, near."])


class DisplayTests(unittest.TestCase):
    def setUp(self):
        server.repeats = server.RepeatFilter(20)

    def test_hazard_cards_carry_the_parts_the_page_draws(self):
        with mock.patch.object(vlm, "describe", return_value=result()):
            response = server.describe(server.DescribeRequest(image=JPEG, lang="hi"))
        card = response.hazards[0]
        self.assertEqual((card.what, card.where, card.distance), ("सीढ़ियाँ", "ahead", "near"))
        self.assertEqual(card.sentence, response.speech.hazards[0])

    def test_a_suppressed_warning_has_no_card(self):
        with mock.patch.object(vlm, "describe", return_value=result()):
            server.describe(server.DescribeRequest(image=JPEG, auto=True))
            again = server.describe(server.DescribeRequest(image=JPEG, auto=True))
        self.assertEqual(again.hazards, [])

    def test_render_rewords_a_scene_in_another_language_without_the_model(self):
        with mock.patch.object(vlm, "describe") as described:
            response = server.render(server.RenderRequest(scene=SCENE, lang="hi"))
        described.assert_not_called()
        self.assertEqual(response.speech.hazards, ["सावधान: सामने सीढ़ियाँ, पास।"])
        self.assertEqual(response.lang, "hi")


class SpeakEndpointTests(unittest.TestCase):
    def test_audio_is_returned_as_wav(self):
        with mock.patch.object(server.tts, "synthesize", return_value=b"RIFFdata"):
            response = server.speak(server.SpeakRequest(text="Hello", lang="en"))
        self.assertEqual((response.media_type, response.body), ("audio/wav", b"RIFFdata"))

    def test_no_voice_gives_503_with_install_instructions(self):
        with mock.patch.object(server.tts, "synthesize", return_value=None):
            response = server.speak(server.SpeakRequest(text="नमस्ते", lang="hi"))
        self.assertEqual(response.status_code, 503)
        self.assertIn("piper.download_voices", body(response)["fix"])

    def test_a_crashing_voice_engine_does_not_crash_the_api(self):
        with mock.patch.object(server.tts, "synthesize", side_effect=RuntimeError("boom")):
            response = server.speak(server.SpeakRequest(text="Hello", lang="en"))
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()

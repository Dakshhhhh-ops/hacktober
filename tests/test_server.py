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


class AccessKeyTests(unittest.TestCase):
    """Phone mode: only a device that opened the link with the key can use the app."""

    def setUp(self):
        from fastapi.testclient import TestClient
        patcher = mock.patch.object(server.config, "ACCESS_KEY", "secret-key")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(server.app, base_url="https://testserver")

    def test_without_the_key_everything_is_refused(self):
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.client.get("/api/health").status_code, 403)
        self.assertEqual(self.client.get("/?key=wrong").status_code, 403)

    def test_the_link_sets_a_cookie_and_removes_the_key_from_the_address(self):
        response = self.client.get("/?key=secret-key", follow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], "/")
        cookie = response.headers["set-cookie"].lower()
        self.assertIn("httponly", cookie)
        self.assertIn("secure", cookie)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_no_key_configured_means_no_check(self):
        with mock.patch.object(server.config, "ACCESS_KEY", ""):
            self.assertEqual(self.client.get("/").status_code, 200)


class MoneyEndpointTests(unittest.TestCase):
    def test_money_is_in_the_envelope_and_spoken(self):
        from drishti.schema import Money
        money = [Money(value=100, kind="note"), Money(value=100, kind="note")]
        found = vlm.Result(scene=Scene.from_summary("Two notes."), find_result=None, status="ok",
                           retries=0, inference_ms=900, request_id="m1", model="test-model",
                           money=money)
        server.repeats = server.RepeatFilter(20)
        with mock.patch.object(vlm, "describe", return_value=found):
            response = server.describe(server.DescribeRequest(image=JPEG, mode="money"))
        self.assertEqual([m.value for m in response.money], [100, 100])
        self.assertEqual(response.speech.rest, ["2 notes of 100 rupees.", "Total 200 rupees."])

    def test_render_rewords_money_in_hindi_without_the_model(self):
        response = server.render(server.RenderRequest(
            scene=Scene.from_summary(""), mode="money", lang="hi",
            money=[{"value": 500, "kind": "note"}]))
        self.assertEqual(response.speech.rest, ["500 रुपये का नोट।"])


class BlurryFrameTests(unittest.TestCase):
    def test_the_page_can_mark_a_frame_as_blurred(self):
        server.repeats = server.RepeatFilter(20)
        with mock.patch.object(vlm, "describe", return_value=result()):
            response = server.describe(server.DescribeRequest(image=JPEG, blurry=True))
        self.assertTrue(response.blurry)
        self.assertIn("blurred", response.speech.rest[0])
        self.assertEqual(response.speech.hazards, ["Careful: stairs ahead, near."])


class InstallableTests(unittest.TestCase):
    def test_the_manifest_and_icon_are_served_with_the_right_types(self):
        from fastapi.testclient import TestClient
        client = TestClient(server.app)
        manifest = client.get("/manifest.webmanifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertTrue(manifest.headers["content-type"].startswith("application/manifest+json"))
        self.assertEqual(manifest.json()["display"], "standalone")
        icon = client.get("/icon.svg")
        self.assertTrue(icon.headers["content-type"].startswith("image/svg+xml"))

    def test_the_page_asks_for_the_manifest_with_the_access_cookie(self):
        page = (server.config.WEB_DIR / "index.html").read_text(encoding="utf-8")
        self.assertIn('rel="manifest" href="manifest.webmanifest" crossorigin="use-credentials"', page)

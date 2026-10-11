"""Voice commands: turning recognised words into actions. The recogniser itself is mocked."""
import json
import unittest
from unittest import mock

from drishti import server, voice


class ParseTests(unittest.TestCase):
    def test_single_word_commands(self):
        self.assertEqual(voice.parse("describe"), {"command": "describe", "target": ""})
        self.assertEqual(voice.parse("read the text"), {"command": "read", "target": ""})
        self.assertEqual(voice.parse("stop"), {"command": "stop", "target": ""})
        self.assertEqual(voice.parse("hindi")["command"], "hindi")

    def test_natural_phrasings_of_describe(self):
        self.assertEqual(voice.parse("what is in front of me")["command"], "describe")
        self.assertEqual(voice.parse("look around")["command"], "describe")

    def test_find_keeps_the_object_and_drops_small_words(self):
        self.assertEqual(voice.parse("find my water bottle"), {"command": "find", "target": "water bottle"})
        self.assertEqual(voice.parse("where is the door"), {"command": "find", "target": "door"})

    def test_find_without_an_object_has_an_empty_target(self):
        self.assertEqual(voice.parse("find"), {"command": "find", "target": ""})

    def test_an_object_on_its_own_is_a_possible_target_not_a_command(self):
        self.assertEqual(voice.parse("bottle"), {"command": "", "target": "bottle"})

    def test_stop_wins_when_several_commands_are_heard(self):
        self.assertEqual(voice.parse("read stop")["command"], "stop")

    def test_nothing_understood(self):
        self.assertEqual(voice.parse(""), {"command": "", "target": ""})

    def test_hindi_commands_and_objects_map_to_english_targets(self):
        self.assertEqual(voice.parse("बताओ", "hi")["command"], "describe")
        self.assertEqual(voice.parse("पढ़ो", "hi")["command"], "read")
        self.assertEqual(voice.parse("मेरी बोतल कहां है", "hi"), {"command": "find", "target": "bottle"})
        self.assertEqual(voice.parse("रुको", "hi")["command"], "stop")


class VocabularyTests(unittest.TestCase):
    def test_every_command_word_is_in_the_vocabulary(self):
        for lang in ("en", "hi"):
            words = voice.vocabulary(lang)
            for triggers in voice.COMMANDS[lang].values():
                for trigger in triggers:
                    self.assertIn(trigger, words)

    def test_english_vocabulary_includes_everyday_objects(self):
        words = voice.vocabulary("en")
        for word in ("bottle", "door", "stairs", "keys"):
            self.assertIn(word, words)


class ListenEndpointTests(unittest.TestCase):
    AUDIO = b"\x00\x00" * voice.SAMPLE_RATE  # one second of silence

    def test_recognised_words_become_a_command(self):
        with mock.patch.object(voice, "available", return_value=True), \
             mock.patch.object(voice, "transcribe", return_value="find my bottle"):
            response = server.listen(self.AUDIO, "en")
        self.assertEqual(response, {"text": "find my bottle", "command": "find", "target": "bottle"})

    def test_missing_speech_model_gives_503_with_a_fix(self):
        with mock.patch.object(voice, "available", return_value=False):
            response = server.listen(self.AUDIO, "hi")
        self.assertEqual(response.status_code, 503)
        self.assertIn("models folder", json.loads(response.body)["fix"])

    def test_audio_that_is_too_short_or_too_long_is_rejected(self):
        with mock.patch.object(voice, "available", return_value=True), \
             mock.patch.object(voice, "transcribe") as transcribe:
            self.assertEqual(server.listen(b"\x00\x00" * 100, "en").status_code, 400)
            too_long = b"\x00\x00" * (voice.SAMPLE_RATE * (voice.MAX_SECONDS + 1))
            self.assertEqual(server.listen(too_long, "en").status_code, 400)
        transcribe.assert_not_called()


if __name__ == "__main__":
    unittest.main()

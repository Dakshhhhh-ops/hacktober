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
        self.assertEqual(voice.parse("Thank you.")["command"], "")

    def test_natural_sentences_with_punctuation(self):
        self.assertEqual(voice.parse("Find my water bottle."), {"command": "find", "target": "water bottle"})
        self.assertEqual(voice.parse("I am looking for my keys"), {"command": "find", "target": "keys"})
        self.assertEqual(voice.parse("Where's the exit?"), {"command": "find", "target": "exit"})
        self.assertEqual(voice.parse("Can you describe what's around me?")["command"], "describe")
        self.assertEqual(voice.parse("Please read this.")["command"], "read")
        self.assertEqual(voice.parse("Stop!")["command"], "stop")

    def test_hindi_punctuation_and_english_words_said_in_hindi(self):
        self.assertEqual(voice.parse("बताओ।", "hi")["command"], "describe")
        self.assertEqual(voice.parse("स्टॉप", "hi")["command"], "stop")
        self.assertEqual(voice.parse("पानी की बोतल कहां है?", "hi"), {"command": "find", "target": "water bottle"})

    def test_a_lone_word_one_letter_off_is_taken_as_the_command(self):
        self.assertEqual(voice.parse("top."), {"command": "stop", "target": ""})
        self.assertEqual(voice.parse("fine")["command"], "find")
        self.assertEqual(voice.parse("reed")["command"], "read")
        # Not when it is part of a sentence, and not for unrelated words.
        self.assertEqual(voice.parse("the table top")["command"], "")
        self.assertEqual(voice.parse("bottle")["command"], "")

    def test_a_string_of_commands_is_treated_as_noise(self):
        # Whisper can repeat its hint on a noisy clip; that must not run a command.
        echo = "describe. read. find my water bottle."
        self.assertEqual(voice.parse(echo), {"command": "", "target": ""})
        # An explicit stop is still honoured.
        self.assertEqual(voice.parse("describe read find stop")["command"], "stop")

    def test_hindi_commands_and_objects_map_to_english_targets(self):
        self.assertEqual(voice.parse("बताओ", "hi")["command"], "describe")
        self.assertEqual(voice.parse("पढ़ो", "hi")["command"], "read")
        self.assertEqual(voice.parse("मेरी बोतल कहां है", "hi"), {"command": "find", "target": "bottle"})
        for stop in ("रुको", "रुक जाओ", "बंद करो", "बस"):
            self.assertEqual(voice.parse(stop, "hi"), {"command": "stop", "target": ""})


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
             mock.patch.object(voice, "engines", return_value=["whisper"]), \
             mock.patch.object(voice, "transcribe", return_value="find my bottle"):
            response = server.listen(self.AUDIO, "en")
        self.assertEqual(response, {"text": "find my bottle", "command": "find", "target": "bottle",
                                    "engine": "whisper"})

    def test_the_second_recogniser_is_tried_when_the_first_hears_no_command(self):
        heard = {"vosk": "का", "whisper": "रुको"}
        with mock.patch.object(voice, "engines", return_value=["vosk", "whisper"]), \
             mock.patch.object(voice, "transcribe", side_effect=lambda pcm, lang, using: heard[using]):
            result = voice.recognise(self.AUDIO, "hi")
        self.assertEqual((result["command"], result["engine"]), ("stop", "whisper"))

    def test_with_no_command_the_first_thing_heard_is_reported(self):
        with mock.patch.object(voice, "engines", return_value=["whisper", "vosk"]), \
             mock.patch.object(voice, "transcribe", side_effect=["thank you", ""]):
            result = voice.recognise(self.AUDIO, "en")
        self.assertEqual((result["text"], result["command"]), ("thank you", ""))

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


class MoneyCommandTests(unittest.TestCase):
    def test_english(self):
        for said in ("money", "how much money is this", "which rupee note is this", "cash"):
            self.assertEqual(voice.parse(said), {"command": "money", "target": ""}, said)

    def test_a_notebook_is_still_something_to_find(self):
        self.assertEqual(voice.parse("find my notebook"), {"command": "find", "target": "notebook"})

    def test_hindi(self):
        self.assertEqual(voice.parse("कितने पैसे हैं", "hi")["command"], "money")
        self.assertEqual(voice.parse("यह कौन सा नोट है", "hi")["command"], "money")

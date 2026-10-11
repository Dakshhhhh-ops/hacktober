"""The Hindi glossary."""
import unittest

from drishti import hindi


class GlossaryTests(unittest.TestCase):
    def test_the_main_noun_is_translated_and_adjectives_dropped(self):
        self.assertEqual(hindi.translate("red plastic barriers"), "बैरिकेड")
        self.assertEqual(hindi.translate("Stairs going down"), "सीढ़ियाँ")
        self.assertEqual(hindi.translate("open sewer manhole"), "खुला मैनहोल")

    def test_the_longest_match_wins(self):
        self.assertEqual(hindi.translate("wet floor"), "गीला फ़र्श")
        self.assertEqual(hindi.translate("open door"), "खुला दरवाज़ा")

    def test_only_whole_words_match(self):
        # "carpet" contains "car" and "plantation" contains "plant".
        self.assertEqual(hindi.translate("carpet"), "carpet")
        self.assertFalse(hindi.is_known("scar tissue"))

    def test_unknown_phrases_are_returned_unchanged(self):
        self.assertEqual(hindi.translate(" gyroscope "), "gyroscope")

    def test_places_are_translated_in_the_order_they_were_said(self):
        self.assertEqual(hindi.translate_place("on the table, to the left"), "मेज़ पर, बाईं ओर")
        self.assertEqual(hindi.translate_place("somewhere odd"), "somewhere odd")


if __name__ == "__main__":
    unittest.main()

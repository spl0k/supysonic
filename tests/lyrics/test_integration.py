# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic.lyrics import Lyrics

from ..api.apitestbase import ApiTestBase
from . import fakes, silent


class LyricsProvidersTestCase(ApiTestBase):
    """Checks getLyrics asks the loaded providers, in order.

    Uses fake providers rather than real ones so it stays about the plumbing.
    """

    __sections__ = {
        "webapp": {"lyrics_providers": f"{silent.__name__} {fakes.__name__}"}
    }

    def setUp(self):
        super().setUp()

        self.silent, self.fake = self._app_layer.lyrics_providers

    def _get_lyrics(self, artist, title):
        rv, child = self._make_request(
            "getLyrics", {"artist": artist, "title": title}, tag="lyrics"
        )
        return child

    def test_first_answer_wins(self):
        child = self._get_lyrics("someone", "something")

        self.assertEqual(child.text, "Fake lyrics")
        self.assertEqual(child.get("artist"), "Fake artist")
        self.assertEqual(child.get("title"), "Fake title")

    def test_asked_with_the_request_values(self):
        self._get_lyrics("someone", "something")

        # Twice each, as the request is made both as GET and POST
        self.assertEqual(self.silent.asked, [("someone", "something")] * 2)
        self.assertEqual(self.fake.asked, [("someone", "something")] * 2)

    def test_stops_at_the_first_answer(self):
        self.silent.answer = Lyrics("Silent", "No more", "Words")

        child = self._get_lyrics("someone", "something")

        self.assertEqual(child.text, "Words")
        self.assertEqual(self.fake.asked, [])

    def test_nobody_answers(self):
        self.fake.answer = None

        child = self._get_lyrics("someone", "something")

        self.assertIsNone(child.text)
        self.assertIsNone(child.get("artist"))


if __name__ == "__main__":
    unittest.main()

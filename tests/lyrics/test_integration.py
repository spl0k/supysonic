# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest

from supysonic.db.models import Album, Artist, Folder, Track
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

        # A track with lyrics in its tags, for what the providers come before
        folder = Folder.create(
            name="Root", path=os.path.abspath("tests/assets/lyrics"), root=True
        )
        artist = Artist.create(name="Artist")
        album = Album.create(artist=artist, name="Album")
        Track.create(
            title="Yay",
            number=1,
            disc=1,
            artist=artist,
            album=album,
            path=os.path.abspath("tests/assets/lyrics/withlyrics.mp3"),
            root_folder=folder,
            folder=folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

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

    def test_providers_come_before_the_library(self):
        child = self._get_lyrics("artist", "yay")

        self.assertEqual(child.text, "Fake lyrics")

    def test_library_when_nobody_answers(self):
        self.fake.answer = None

        child = self._get_lyrics("artist", "yay")

        self.assertIn("Some words", child.text)


if __name__ == "__main__":
    unittest.main()

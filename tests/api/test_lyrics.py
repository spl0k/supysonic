# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest

from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase


class LyricsTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        folder = Folder.create(
            name="Root",
            path=os.path.abspath("tests/assets/lyrics"),
            root=True,
        )

        artist = Artist.create(name="Artist")
        album = Album.create(artist=artist, name="Album")

        Track.create(
            title="Nope",
            number=1,
            disc=1,
            artist=artist,
            album=album,
            path=os.path.abspath("tests/assets/lyrics/empty.mp3"),
            root_folder=folder,
            folder=folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )
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

    def test_get_lyrics(self):
        self._make_request("getLyrics", error=10)
        self._make_request("getLyrics", {"artist": "artist"}, error=10)
        self._make_request("getLyrics", {"title": "title"}, error=10)

        # No matching track: empty lyrics
        rv, child = self._make_request(
            "getLyrics",
            {
                "artist": "some really long name hoping",
                "title": "to get absolutely no result",
            },
            tag="lyrics",
        )
        self.assertIsNone(child.text)

        # Local file
        rv, child = self._make_request(
            "getLyrics", {"artist": "artist", "title": "nope"}, tag="lyrics"
        )
        self.assertIn("text file", child.text)

        # Metadata
        rv, child = self._make_request(
            "getLyrics", {"artist": "artist", "title": "yay"}, tag="lyrics"
        )
        self.assertIn("Some words", child.text)


if __name__ == "__main__":
    unittest.main()

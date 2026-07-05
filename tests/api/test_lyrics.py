# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import shutil
import tempfile
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

    def test_get_lyrics_bad_encoding(self):
        # A lyrics file that can't be decoded is skipped (logged, not errored),
        # leaving no lyrics to return.
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        track_path = os.path.join(d, "bad.mp3")
        shutil.copyfile(os.path.abspath("tests/assets/lyrics/empty.mp3"), track_path)
        # Bytes undefined in both cp1252 and utf-8, so decoding fails on every OS
        with open(os.path.join(d, "bad.txt"), "wb") as f:
            f.write(b"\x81\x8d\x8f\x90\x9d")

        artist = Artist.get(name="Artist")
        album = Album.get(name="Album")
        folder = Folder.get(name="Root")
        Track.create(
            title="Badly Encoded",
            number=1,
            disc=1,
            artist=artist,
            album=album,
            path=track_path,
            root_folder=folder,
            folder=folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

        rv, child = self._make_request(
            "getLyrics",
            {"artist": "artist", "title": "Badly Encoded"},
            tag="lyrics",
        )
        self.assertIsNone(child.text)


if __name__ == "__main__":
    unittest.main()

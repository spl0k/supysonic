# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from supysonic.db.models import Album, Artist, Folder, Track
from supysonic.lyrics import Lyrics
from supysonic.lyrics.sidecar import SidecarLyricsProvider

from ..testbase import TestBase

ASSETS = os.path.abspath("tests/assets/lyrics")


class SidecarLyricsProviderTestCase(TestBase):
    def setUp(self):
        super().setUp()

        self.folder = Folder.create(name="Root", path=ASSETS, root=True)
        self.artist = Artist.create(name="Artist")
        self.album = Album.create(artist=self.artist, name="Album")

        self.provider = SidecarLyricsProvider(self.config)

    def _track(self, title, path):
        return Track.create(
            title=title,
            number=1,
            disc=1,
            artist=self.artist,
            album=self.album,
            path=path,
            root_folder=self.folder,
            folder=self.folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

    def _badly_encoded(self):
        """A track whose lyrics file can't be decoded."""

        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        path = os.path.join(d, "bad.mp3")
        shutil.copyfile(os.path.join(ASSETS, "empty.mp3"), path)
        # Bytes undefined in both cp1252 and utf-8, so decoding fails on every OS
        with open(os.path.join(d, "bad.txt"), "wb") as f:
            f.write(b"\x81\x8d\x8f\x90\x9d")

        return path

    def test_configured(self):
        self.assertTrue(self.provider.configured)

    def test_found(self):
        self._track("Nope", os.path.join(ASSETS, "empty.mp3"))

        self.assertEqual(
            self.provider.get_lyrics("art", "no"),
            Lyrics(
                "Artist",
                "Nope",
                "Lyrics in a text file next to a track without metadata.\n",
            ),
        )

    def test_no_matching_track(self):
        self._track("Nope", os.path.join(ASSETS, "empty.mp3"))

        self.assertIsNone(self.provider.get_lyrics("someone", "something"))

    def test_no_lyrics_file(self):
        # Lyrics in the tags are none of this provider's business
        self._track("Yay", os.path.join(ASSETS, "withlyrics.mp3"))

        self.assertIsNone(self.provider.get_lyrics("artist", "yay"))

    def test_next_candidate(self):
        # Candidates are tried until one has a lyrics file
        self._track("Song A", os.path.join(ASSETS, "withlyrics.mp3"))
        self._track("Song B", os.path.join(ASSETS, "empty.mp3"))

        self.assertEqual(self.provider.get_lyrics("artist", "song").title, "Song B")

    def test_bad_encoding(self):
        # Skipped, and logged rather than turned into an API error
        self._track("Badly Encoded", self._badly_encoded())

        with self.assertLogs("supysonic.lyrics.sidecar", "WARNING"):
            self.assertIsNone(self.provider.get_lyrics("artist", "badly"))

    def test_bad_encoding_then_next_candidate(self):
        self._track("Song A", self._badly_encoded())
        self._track("Song B", os.path.join(ASSETS, "empty.mp3"))

        with self.assertLogs("supysonic.lyrics.sidecar", "WARNING"):
            lyrics = self.provider.get_lyrics("artist", "song")

        self.assertEqual(lyrics.title, "Song B")

    def test_unreadable_file(self):
        self._track("Nope", os.path.join(ASSETS, "empty.mp3"))

        with patch("builtins.open", side_effect=PermissionError("denied")):
            with self.assertLogs("supysonic.lyrics.sidecar", "WARNING"):
                self.assertIsNone(self.provider.get_lyrics("artist", "nope"))


if __name__ == "__main__":
    unittest.main()

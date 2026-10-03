# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest
from unittest.mock import Mock, patch

import mediafile

from supysonic.db.models import Album, Artist, Folder, Track
from supysonic.lyrics import Lyrics
from supysonic.lyrics.embedded import EmbeddedLyricsProvider

from ..testbase import TestBase


class EmbeddedLyricsProviderTestCase(TestBase):
    def setUp(self):
        super().setUp()

        self.folder = Folder.create(
            name="Root", path=os.path.abspath("tests/assets/lyrics"), root=True
        )
        self.artist = Artist.create(name="Artist")
        self.album = Album.create(artist=self.artist, name="Album")

        self.provider = EmbeddedLyricsProvider(self.config)

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

    def _tagged_with(self, lyrics):
        """Have every file read as if tagged with ``lyrics``.

        ID3 cuts its text frames at the first NUL, so the padding some taggers
        leave behind can't be reproduced with an actual file.
        """

        return patch.object(mediafile, "MediaFile", return_value=Mock(lyrics=lyrics))

    def test_configured(self):
        self.assertTrue(self.provider.configured)

    def test_found(self):
        self._track("Yay", os.path.abspath("tests/assets/lyrics/withlyrics.mp3"))

        self.assertEqual(
            self.provider.get_lyrics("art", "ya"),
            Lyrics("Artist", "Yay", "Some words here. Now sing with me!"),
        )

    def test_no_matching_track(self):
        self._track("Yay", os.path.abspath("tests/assets/lyrics/withlyrics.mp3"))

        self.assertIsNone(self.provider.get_lyrics("someone", "something"))

    def test_no_lyrics_tag(self):
        self._track("Nope", os.path.abspath("tests/assets/lyrics/empty.mp3"))

        self.assertIsNone(self.provider.get_lyrics("artist", "nope"))

    def test_blank_lyrics_tag(self):
        # NUL padding and whitespace don't count as lyrics
        self._track("Blank", os.path.abspath("tests/assets/lyrics/empty.mp3"))

        with self._tagged_with("\x00 \n\x00"):
            self.assertIsNone(self.provider.get_lyrics("artist", "blank"))

    def test_padding_is_stripped(self):
        self._track("Padded", os.path.abspath("tests/assets/lyrics/empty.mp3"))

        with self._tagged_with("\x00 Some words\n\x00"):
            lyrics = self.provider.get_lyrics("artist", "padded")

        self.assertEqual(lyrics.text, "Some words")

    def test_next_candidate(self):
        # Candidates are tried until one has lyrics
        self._track("Song A", os.path.abspath("tests/assets/lyrics/empty.mp3"))
        self._track("Song B", os.path.abspath("tests/assets/lyrics/withlyrics.mp3"))

        self.assertEqual(self.provider.get_lyrics("artist", "song").title, "Song B")

    def test_unreadable_file(self):
        # A file gone missing since the last scan is skipped, not an API error
        self._track("Song A", os.path.abspath("tests/assets/lyrics/missing.mp3"))
        self._track("Song B", os.path.abspath("tests/assets/lyrics/withlyrics.mp3"))

        with self.assertLogs("supysonic.lyrics.embedded", "WARNING"):
            lyrics = self.provider.get_lyrics("artist", "song")

        self.assertEqual(lyrics.title, "Song B")


if __name__ == "__main__":
    unittest.main()

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

import mediafile
from PIL import Image

from supysonic.covers.embedded import EmbeddedCoverArtProvider
from supysonic.db.models import Album, Artist, Folder, Track

from ..testbase import TestBase

WITH_ART = os.path.abspath("tests/assets/formats/silence.mp3")
WITHOUT_ART = os.path.abspath("tests/assets/lyrics/empty.mp3")
UNREADABLE = os.path.abspath("tests/assets/23bytes")


class EmbeddedCoverArtProviderTestCase(TestBase):
    def setUp(self):
        super().setUp()

        self.root = Folder.create(name="Root", path=os.path.abspath("tests"), root=True)
        self.folder = Folder.create(
            name="Folder",
            path=os.path.abspath("tests/assets"),
            root=False,
            parent=self.root,
        )
        self.artist = Artist.create(name="Artist")
        self.album = Album.create(artist=self.artist, name="Album")

        self.provider = EmbeddedCoverArtProvider(self.config)

    def _track(self, path, has_art=False, folder=None, album=None):
        return Track.create(
            title=os.path.basename(path),
            number=1,
            disc=1,
            artist=self.artist,
            album=album or self.album,
            path=path,
            root_folder=self.root,
            folder=folder or self.folder,
            duration=2,
            bitrate=320,
            has_art=has_art,
            last_modification=0,
        )

    def test_configured(self):
        self.assertTrue(self.provider.configured)

    def test_find_covers_nothing(self):
        self.assertEqual(self.provider.find_covers([]), {})

    def test_find_covers_tracks(self):
        with_art = self._track(WITH_ART, has_art=True)
        without_art = self._track(WITHOUT_ART)

        covers = self.provider.find_covers([with_art, without_art])

        # A track's cover is its own
        self.assertEqual(covers, {with_art.id: with_art.id})

    def test_find_covers_folders(self):
        with_art = self._track(WITH_ART, has_art=True)
        self._track(WITHOUT_ART, folder=self.root)

        covers = self.provider.find_covers([self.root, self.folder])

        # Folders fall back on one of their tracks
        self.assertEqual(covers, {self.folder.id: with_art.id})

    def test_find_covers_albums(self):
        other = Album.create(artist=self.artist, name="Other")
        empty = Album.create(artist=self.artist, name="Empty")
        with_art = self._track(WITH_ART, has_art=True)
        self._track(WITHOUT_ART, album=other)

        covers = self.provider.find_covers([self.album, other, empty])

        # Albums fall back on one of their tracks
        self.assertEqual(covers, {self.album.id: with_art.id})

    def test_get_cover(self):
        cover = self.provider.get_cover(self._track(WITH_ART, has_art=True))

        self.assertIsNone(cover.path)
        with Image.open(BytesIO(cover.data)) as im:
            self.assertEqual(im.format, "PNG")

    def test_get_cover_without_art(self):
        self.assertIsNone(self.provider.get_cover(self._track(WITHOUT_ART)))

    def test_get_cover_empty_art(self):
        track = self._track(WITH_ART, has_art=True)

        with patch.object(mediafile, "MediaFile", return_value=Mock(art=b"")):
            self.assertIsNone(self.provider.get_cover(track))

    def test_get_cover_unreadable_file(self):
        track = self._track(UNREADABLE, has_art=True)

        with self.assertLogs("supysonic.covers.embedded", "WARNING"):
            self.assertIsNone(self.provider.get_cover(track))

    def test_get_cover_not_a_track(self):
        # Neither owns the cover of the track they fall back on
        self._track(WITH_ART, has_art=True)

        self.assertIsNone(self.provider.get_cover(self.folder))
        self.assertIsNone(self.provider.get_cover(self.album))


if __name__ == "__main__":
    unittest.main()

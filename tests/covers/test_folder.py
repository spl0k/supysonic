# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import unittest
from unittest.mock import patch

from supysonic.covers import Cover
from supysonic.covers.folder import FolderCoverArtProvider
from supysonic.db.models import Album, Artist, Folder, Track

from ..testbase import TestBase

ASSETS = os.path.abspath("tests/assets")


class FolderCoverArtProviderTestCase(TestBase):
    def setUp(self):
        super().setUp()

        self.root = Folder.create(name="Root", path=os.path.dirname(ASSETS), root=True)
        self.with_cover = Folder.create(
            name="Covered",
            path=ASSETS,
            root=False,
            parent=self.root,
            cover_art="cover.jpg",
        )
        self.artist = Artist.create(name="Artist")

        self.provider = FolderCoverArtProvider(self.config)

    def _track(self, folder, album):
        return Track.create(
            title="Track",
            number=1,
            disc=1,
            artist=self.artist,
            album=album,
            path=os.path.join(ASSETS, f"{folder.name}-{album.name}"),
            root_folder=self.root,
            folder=folder,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

    def test_configured(self):
        self.assertTrue(self.provider.configured)

    def test_find_covers_nothing(self):
        self.assertEqual(self.provider.find_covers([]), {})

    def test_find_covers_folders(self):
        # A folder's cover is its own
        covers = self.provider.find_covers([self.root, self.with_cover])

        self.assertEqual(covers, {self.with_cover.id: self.with_cover.id})

    def test_find_covers_tracks(self):
        album = Album.create(artist=self.artist, name="Album")
        covered = self._track(self.with_cover, album)
        uncovered = self._track(self.root, album)

        covers = self.provider.find_covers([covered, uncovered])

        # Tracks fall back on their folder's
        self.assertEqual(covers, {covered.id: self.with_cover.id})

    def test_find_covers_albums(self):
        covered = Album.create(artist=self.artist, name="Covered")
        partly = Album.create(artist=self.artist, name="Partly")
        uncovered = Album.create(artist=self.artist, name="Uncovered")
        empty = Album.create(artist=self.artist, name="Empty")
        self._track(self.with_cover, covered)
        self._track(self.root, partly)
        self._track(self.with_cover, partly)
        self._track(self.root, uncovered)

        covers = self.provider.find_covers([covered, partly, uncovered, empty])

        # Albums fall back on the folder of one of their tracks
        self.assertEqual(
            covers,
            {covered.id: self.with_cover.id, partly.id: self.with_cover.id},
        )

    def test_get_cover(self):
        cover = self.provider.get_cover(self.with_cover)

        self.assertEqual(cover, Cover(path=os.path.join(ASSETS, "cover.jpg")))

    def test_get_cover_none(self):
        self.assertIsNone(self.provider.get_cover(self.root))

    def test_get_cover_missing_file(self):
        self.with_cover.cover_art = "gone.jpg"

        self.assertIsNone(self.provider.get_cover(self.with_cover))

    def test_get_cover_not_a_folder(self):
        # Neither owns the cover of the folder they fall back on
        album = Album.create(artist=self.artist, name="Album")
        track = self._track(self.with_cover, album)

        self.assertIsNone(self.provider.get_cover(track))
        self.assertIsNone(self.provider.get_cover(album))

    def test_artists(self):
        # Nothing for them, not even a query to find it out
        with patch.object(Track, "select", side_effect=AssertionError):
            self.assertEqual(self.provider.find_covers([self.artist]), {})

        self.assertIsNone(self.provider.get_cover(self.artist))


if __name__ == "__main__":
    unittest.main()

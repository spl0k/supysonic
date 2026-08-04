# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Tests for db.SerializationContext, the per-request annotation batcher that
replaces the per-item starred/rating/avg-rating lookups in the as_subsonic_*
serializers (audit finding H9).

The query-count assertions are the actual regression guard: the number of SQL
statements a loader issues must be constant, independent of the collection size.
"""

import logging
import unittest

from supysonic.db import (
    Album,
    Artist,
    Folder,
    RatingFolder,
    RatingTrack,
    SerializationContext,
    StarredAlbum,
    StarredArtist,
    StarredFolder,
    StarredTrack,
    Track,
    User,
)

from ._dataset import populate_library
from .apitestbase import ApiTestBase


class _QueryCounter(logging.Handler):
    """Counts the SQL statements peewee logs at DEBUG."""

    def __init__(self):
        super().__init__()
        self.count = 0

    def emit(self, record):
        self.count += 1


class SerializationContextTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        self.lib = populate_library()
        self.alice = User.get(name="alice")
        self.bob = User.get(name="bob")

        tracks = self.lib.tracks
        # alice stars + rates track 0, stars track 1, rates nothing else.
        StarredTrack.create(user=self.alice, starred=tracks[0])
        StarredTrack.create(user=self.alice, starred=tracks[1])
        RatingTrack.create(user=self.alice, rated=tracks[0], rating=5)
        # bob's rating feeds the (not user-scoped) average but not userRating.
        RatingTrack.create(user=self.bob, rated=tracks[0], rating=3)

        StarredAlbum.create(user=self.alice, starred=self.lib.albums.dsotm)
        StarredArtist.create(user=self.alice, starred=self.lib.artists.pink_floyd)
        StarredFolder.create(user=self.alice, starred=self.lib.folders.rock)
        RatingFolder.create(user=self.alice, rated=self.lib.folders.rock, rating=4)

    def _count_queries(self, fn):
        logger = logging.getLogger("peewee")
        handler = _QueryCounter()
        old_level = logger.level
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        try:
            fn()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old_level)
        return handler.count

    # --- query-count regression guards -------------------------------------

    def test_add_tracks_query_count_is_constant(self):
        tracks = self.lib.tracks
        # 3 annotation queries (starred IN, rating IN, avg group-by) + 3 FK
        # preloads (folders, albums, artists) == 6, whatever N.
        full = self._count_queries(
            lambda: SerializationContext(self.alice).add_tracks(tracks)
        )
        half = self._count_queries(
            lambda: SerializationContext(self.alice).add_tracks(tracks[:4])
        )
        self.assertEqual(full, 6)
        self.assertEqual(half, 6)

    def test_add_folders_query_count_is_constant(self):
        folders = list(Folder.select())  # roots + children
        self.assertGreater(len(folders), 1)
        # 3 annotation queries + 1 parent preload.
        n = self._count_queries(
            lambda: SerializationContext(self.alice).add_folders(folders)
        )
        self.assertEqual(n, 4)

    def test_add_artists_and_albums_query_count(self):
        artists = list(Artist.select())
        albums = list(Album.select())
        # artists: 1 (starred only, no FK to preload).
        self.assertEqual(
            self._count_queries(
                lambda: SerializationContext(self.alice).add_artists(artists)
            ),
            1,
        )
        # albums: 1 (starred) + 1 (artist preload).
        self.assertEqual(
            self._count_queries(
                lambda: SerializationContext(self.alice).add_albums(albums)
            ),
            2,
        )

    def test_preloaded_fks_issue_no_queries(self):
        # The Pass 2 guarantee: after add_*, the foreign keys a serializer
        # dereferences are already loaded. Full track serialization touches
        # album/artist/folder/root_folder; folders expose parent; albums expose
        # artist. None of it should hit the database. (Folder cover-art and
        # album aggregates remain per-item until Pass 3, so they're excluded.)
        tracks = self.lib.tracks
        folders = list(Folder.select().where(~Folder.root))
        albums = list(Album.select())
        ctx = SerializationContext(self.alice, prefs=None)
        ctx.add_tracks(tracks)
        ctx.add_folders(folders)
        ctx.add_albums(albums)

        def touch_fks():
            for t in tracks:
                t.as_subsonic_child(ctx)  # album/artist/folder/root_folder
            for f in folders:
                _ = (f.parent.id, f.parent.name)
            for a in albums:
                _ = (a.artist.id, a.artist.name)

        self.assertEqual(self._count_queries(touch_fks), 0)

    def test_empty_collections_issue_no_queries(self):
        ctx = SerializationContext(self.alice)
        self.assertEqual(self._count_queries(lambda: ctx.add_tracks([])), 0)
        self.assertEqual(self._count_queries(lambda: ctx.add_folders([])), 0)
        self.assertEqual(self._count_queries(lambda: ctx.add_artists([])), 0)
        self.assertEqual(self._count_queries(lambda: ctx.add_albums([])), 0)

    # --- found / absent branches -------------------------------------------

    def test_found_and_absent_track_annotations(self):
        tracks = self.lib.tracks
        ctx = SerializationContext(self.alice)
        ctx.add_tracks(tracks)

        annotated = tracks[0].as_subsonic_child(ctx)
        self.assertIn("starred", annotated)
        self.assertEqual(annotated["userRating"], 5)
        self.assertEqual(annotated["averageRating"], 4)  # avg of 5 and 3

        plain = tracks[2].as_subsonic_child(ctx)
        self.assertNotIn("starred", plain)
        self.assertNotIn("userRating", plain)
        self.assertNotIn("averageRating", plain)

    def test_context_is_user_scoped(self):
        # Track 0: alice starred + rated 5, bob rated 3. From bob's context
        # alice's star must not leak and the rating must be bob's own (3),
        # while the (library-wide) average stays 4.
        tracks = self.lib.tracks
        ctx = SerializationContext(self.bob)
        ctx.add_tracks(tracks)
        info = tracks[0].as_subsonic_child(ctx)
        self.assertNotIn("starred", info)  # alice's star must not leak
        self.assertEqual(info["userRating"], 3)  # bob's own rating, not alice's 5
        self.assertEqual(info["averageRating"], 4)

        # Track 1: alice starred it, bob did nothing → fully clean for bob.
        clean = tracks[1].as_subsonic_child(ctx)
        self.assertNotIn("starred", clean)
        self.assertNotIn("userRating", clean)
        self.assertNotIn("averageRating", clean)


if __name__ == "__main__":
    unittest.main()

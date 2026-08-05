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
        # 3 annotation queries + parent preload + cover-art preload == 5.
        n = self._count_queries(
            lambda: SerializationContext(self.alice).add_folders(folders)
        )
        self.assertEqual(n, 5)

    def test_add_artists_and_albums_query_count(self):
        artists = list(Artist.select())
        albums = list(Album.select())
        # artists: starred + album-count aggregate == 2.
        self.assertEqual(
            self._count_queries(
                lambda: SerializationContext(self.alice).add_artists(artists)
            ),
            2,
        )
        # albums: starred + artist preload + agg + genre + cover(folder) +
        # cover(has-art fallback) == 6.
        self.assertEqual(
            self._count_queries(
                lambda: SerializationContext(self.alice).add_albums(albums)
            ),
            6,
        )

    def test_full_serialization_issues_no_queries(self):
        # The end goal (Passes 2+3): after add_*, serializing every item in a
        # collection touches the database zero times -- FKs preloaded,
        # annotations and all sub-aggregates (cover art, album duration/count/
        # genre, artist album count) cached.
        tracks = self.lib.tracks
        folders = list(Folder.select().where(~Folder.root))
        albums = list(Album.select())
        artists = list(Artist.select())
        ctx = SerializationContext(self.alice, prefs=None)
        ctx.add_tracks(tracks)
        ctx.add_folders(folders)
        ctx.add_albums(albums)
        ctx.add_artists(artists)

        def serialize_all():
            for t in tracks:
                t.as_subsonic_child(ctx)
            for f in folders:
                f.as_subsonic_child(ctx)  # cover-art loop now batched
                f.as_subsonic_artist(ctx)
            for a in albums:
                a.as_subsonic_album(ctx)  # aggregates now batched
            for a in artists:
                a.as_subsonic_artist(ctx)  # albumCount now batched

        self.assertEqual(self._count_queries(serialize_all), 0)

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

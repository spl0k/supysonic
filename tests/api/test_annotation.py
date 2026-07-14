# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import uuid

from supysonic.db import (
    Album,
    Artist,
    ClientPrefs,
    Folder,
    SerializationContext,
    Track,
    User,
)

from .apitestbase import ApiTestBase


class AnnotationTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        root = Folder.create(name="Root", root=True, path="tests")
        folder = Folder.create(
            name="Folder", root=False, path="tests/assets", parent=root
        )
        artist = Artist.create(name="Artist")
        album = Album.create(name="Album", artist=artist)

        # Populate folder ids
        root = Folder.get(name="Root")
        folder = Folder.get(name="Folder")

        track = Track.create(
            title="Track",
            album=album,
            artist=artist,
            disc=1,
            number=1,
            path="tests/assets/empty",
            folder=folder,
            root_folder=root,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

        self.folderid = folder.id
        self.artistid = artist.id
        self.albumid = album.id
        self.trackid = track.id
        self.user = User.get(name="alice")
        self.prefs = ClientPrefs.create(user=self.user, client_name="tests")

    def _ser(self, entity):
        """Serialize a single entity through a freshly-built context."""
        ctx = SerializationContext(self.user, self.prefs)
        if isinstance(entity, Track):
            ctx.add_tracks([entity])
            return entity.as_subsonic_child(ctx)
        if isinstance(entity, Folder):
            ctx.add_folders([entity])
            return entity.as_subsonic_child(ctx)
        if isinstance(entity, Album):
            ctx.add_albums([entity])
            return entity.as_subsonic_album(ctx)
        ctx.add_artists([entity])
        return entity.as_subsonic_artist(ctx)

    def test_star(self):
        self._make_request("star", error=10)
        self._make_request("star", {"id": "unknown"}, error=0)
        self._make_request("star", {"albumId": "unknown"}, error=0)
        self._make_request("star", {"artistId": "unknown"}, error=0)
        self._make_request("star", {"id": str(uuid.uuid4())}, error=70)
        self._make_request("star", {"albumId": str(uuid.uuid4())}, error=70)
        self._make_request("star", {"artistId": str(uuid.uuid4())}, error=70)

        self._make_request("star", {"id": str(self.artistid)}, error=70)
        self._make_request("star", {"id": str(self.albumid)}, error=70)
        self._make_request("star", {"id": str(self.trackid)}, skip_post=True)
        self.assertIn("starred", self._ser(Track[self.trackid]))
        self._make_request("star", {"id": str(self.trackid)}, error=0)

        self._make_request("star", {"id": str(self.folderid)}, skip_post=True)
        self.assertIn("starred", self._ser(Folder[self.folderid]))
        self._make_request("star", {"id": str(self.folderid)}, error=0)

        self._make_request("star", {"albumId": str(self.folderid)}, error=0)
        self._make_request("star", {"albumId": str(self.artistid)}, error=70)
        self._make_request("star", {"albumId": str(self.trackid)}, error=70)
        self._make_request("star", {"albumId": str(self.albumid)}, skip_post=True)
        self.assertIn("starred", self._ser(Album[self.albumid]))
        self._make_request("star", {"albumId": str(self.albumid)}, error=0)

        self._make_request("star", {"artistId": str(self.folderid)}, error=0)
        self._make_request("star", {"artistId": str(self.albumid)}, error=70)
        self._make_request("star", {"artistId": str(self.trackid)}, error=70)
        self._make_request("star", {"artistId": str(self.artistid)}, skip_post=True)
        self.assertIn("starred", self._ser(Artist[self.artistid]))
        self._make_request("star", {"artistId": str(self.artistid)}, error=0)

    def test_unstar(self):
        self._make_request(
            "star",
            {
                "id": [str(self.folderid), str(self.trackid)],
                "artistId": str(self.artistid),
                "albumId": str(self.albumid),
            },
            skip_post=True,
        )

        self._make_request("unstar", error=10)
        self._make_request("unstar", {"id": "unknown"}, error=0)
        self._make_request("unstar", {"albumId": "unknown"}, error=0)
        self._make_request("unstar", {"artistId": "unknown"}, error=0)

        self._make_request("unstar", {"id": str(self.trackid)}, skip_post=True)
        self.assertNotIn("starred", self._ser(Track[self.trackid]))

        self._make_request("unstar", {"id": str(self.folderid)}, skip_post=True)
        self.assertNotIn("starred", self._ser(Folder[self.folderid]))

        self._make_request("unstar", {"albumId": str(self.albumid)}, skip_post=True)
        self.assertNotIn("starred", self._ser(Album[self.albumid]))

        self._make_request("unstar", {"artistId": str(self.artistid)}, skip_post=True)
        self.assertNotIn("starred", self._ser(Artist[self.artistid]))

    def test_set_rating(self):
        self._make_request("setRating", error=10)
        self._make_request("setRating", {"id": str(self.trackid)}, error=10)
        self._make_request("setRating", {"rating": 3}, error=10)
        self._make_request("setRating", {"id": "string", "rating": 3}, error=0)
        self._make_request(
            "setRating", {"id": str(uuid.uuid4()), "rating": 3}, error=70
        )
        self._make_request(
            "setRating", {"id": str(self.artistid), "rating": 3}, error=70
        )
        self._make_request(
            "setRating", {"id": str(self.albumid), "rating": 3}, error=70
        )
        self._make_request(
            "setRating", {"id": str(self.trackid), "rating": "string"}, error=0
        )
        self._make_request(
            "setRating", {"id": str(self.trackid), "rating": -1}, error=0
        )
        self._make_request("setRating", {"id": str(self.trackid), "rating": 6}, error=0)

        self.assertNotIn("userRating", self._ser(Track[self.trackid]))

        for i in range(1, 6):
            self._make_request(
                "setRating", {"id": str(self.trackid), "rating": i}, skip_post=True
            )
            self.assertEqual(
                self._ser(Track[self.trackid])["userRating"],
                i,
            )

        self._make_request(
            "setRating", {"id": str(self.trackid), "rating": 0}, skip_post=True
        )
        self.assertNotIn("userRating", self._ser(Track[self.trackid]))

        self.assertNotIn("userRating", self._ser(Folder[self.folderid]))
        for i in range(1, 6):
            self._make_request(
                "setRating", {"id": str(self.folderid), "rating": i}, skip_post=True
            )
            self.assertEqual(self._ser(Folder[self.folderid])["userRating"], i)
        self._make_request(
            "setRating", {"id": str(self.folderid), "rating": 0}, skip_post=True
        )
        self.assertNotIn("userRating", self._ser(Folder[self.folderid]))

    def test_scrobble(self):
        self._make_request("scrobble", error=10)
        self._make_request("scrobble", {"id": "song"}, error=0)
        self._make_request("scrobble", {"id": str(uuid.uuid4())}, error=70)
        self._make_request("scrobble", {"id": str(self.folderid)}, error=0)

        self._make_request("scrobble", {"id": str(self.trackid)})
        self._make_request("scrobble", {"id": str(self.trackid), "submission": True})
        self._make_request("scrobble", {"id": str(self.trackid), "submission": False})


if __name__ == "__main__":
    unittest.main()

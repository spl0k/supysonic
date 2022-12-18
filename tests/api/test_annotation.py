# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import uuid

from supysonic.db import Folder, Artist, Album, Track, User, ClientPrefs

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
        self.assertIn(
            "starred", Track[self.trackid].as_subsonic_child(self.user, self.prefs)
        )
        self._make_request("star", {"id": str(self.trackid)}, error=0)

        self._make_request("star", {"id": str(self.folderid)}, skip_post=True)
        self.assertIn("starred", Folder[self.folderid].as_subsonic_child(self.user))
        self._make_request("star", {"id": str(self.folderid)}, error=0)

        self._make_request("star", {"albumId": str(self.folderid)}, error=0)
        self._make_request("star", {"albumId": str(self.artistid)}, error=70)
        self._make_request("star", {"albumId": str(self.trackid)}, error=70)
        self._make_request("star", {"albumId": str(self.albumid)}, skip_post=True)
        self.assertIn("starred", Album[self.albumid].as_subsonic_album(self.user))
        self._make_request("star", {"albumId": str(self.albumid)}, error=0)

        self._make_request("star", {"artistId": str(self.folderid)}, error=0)
        self._make_request("star", {"artistId": str(self.albumid)}, error=70)
        self._make_request("star", {"artistId": str(self.trackid)}, error=70)
        self._make_request("star", {"artistId": str(self.artistid)}, skip_post=True)
        self.assertIn("starred", Artist[self.artistid].as_subsonic_artist(self.user))
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
        self.assertNotIn(
            "starred", Track[self.trackid].as_subsonic_child(self.user, self.prefs)
        )

        self._make_request("unstar", {"id": str(self.folderid)}, skip_post=True)
        self.assertNotIn("starred", Folder[self.folderid].as_subsonic_child(self.user))

        self._make_request("unstar", {"albumId": str(self.albumid)}, skip_post=True)
        self.assertNotIn("starred", Album[self.albumid].as_subsonic_album(self.user))

        self._make_request("unstar", {"artistId": str(self.artistid)}, skip_post=True)
        self.assertNotIn("starred", Artist[self.artistid].as_subsonic_artist(self.user))

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

        self.assertNotIn(
            "userRating", Track[self.trackid].as_subsonic_child(self.user, self.prefs)
        )

        for i in range(1, 6):
            self._make_request(
                "setRating", {"id": str(self.trackid), "rating": i}, skip_post=True
            )
            self.assertEqual(
                Track[self.trackid].as_subsonic_child(self.user, self.prefs)[
                    "userRating"
                ],
                i,
            )

        self._make_request(
            "setRating", {"id": str(self.trackid), "rating": 0}, skip_post=True
        )
        self.assertNotIn(
            "userRating", Track[self.trackid].as_subsonic_child(self.user, self.prefs)
        )

        self.assertNotIn(
            "userRating", Folder[self.folderid].as_subsonic_child(self.user)
        )
        for i in range(1, 6):
            self._make_request(
                "setRating", {"id": str(self.folderid), "rating": i}, skip_post=True
            )
            self.assertEqual(
                Folder[self.folderid].as_subsonic_child(self.user)["userRating"], i
            )
        self._make_request(
            "setRating", {"id": str(self.folderid), "rating": 0}, skip_post=True
        )
        self.assertNotIn(
            "userRating", Folder[self.folderid].as_subsonic_child(self.user)
        )

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

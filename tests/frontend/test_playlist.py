# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import uuid

from supysonic.db import Folder, Artist, Album, Track, Playlist, User

from .frontendtestbase import FrontendTestBase


class PlaylistTestCase(FrontendTestBase):
    def setUp(self):
        super().setUp()

        folder = Folder.create(name="Root", path="tests/assets", root=True)
        artist = Artist.create(name="Artist!")
        album = Album.create(name="Album!", artist=artist)

        track = Track.create(
            path="tests/assets/23bytes",
            title="23bytes",
            artist=artist,
            album=album,
            folder=folder,
            root_folder=folder,
            duration=2,
            disc=1,
            number=1,
            bitrate=320,
            last_modification=0,
        )

        playlist = Playlist.create(name="Playlist!", user=User.get(name="alice"))
        for _ in range(4):
            playlist.add(track)
        playlist.save()

        self.playlistid = playlist.id

    def test_index(self):
        self._login("alice", "Alic3")
        rv = self.client.get("/playlist")
        self.assertIn("My playlists", rv.data)

    def test_details(self):
        self._login("alice", "Alic3")
        rv = self.client.get("/playlist/string", follow_redirects=True)
        self.assertIn("Invalid", rv.data)
        rv = self.client.get("/playlist/" + str(uuid.uuid4()), follow_redirects=True)
        self.assertIn("Unknown", rv.data)
        rv = self.client.get("/playlist/" + str(self.playlistid))
        self.assertIn("Playlist!", rv.data)
        self.assertIn("23bytes", rv.data)
        self.assertIn("Artist!", rv.data)
        self.assertIn("Album!", rv.data)

    def test_update(self):
        self._login("bob", "B0b")
        rv = self.client.post("/playlist/string", follow_redirects=True)
        self.assertIn("Invalid", rv.data)
        rv = self.client.post("/playlist/" + str(uuid.uuid4()), follow_redirects=True)
        self.assertIn("Unknown", rv.data)
        rv = self.client.post(
            "/playlist/" + str(self.playlistid), follow_redirects=True
        )
        self.assertNotIn("updated", rv.data)
        self.assertIn("not allowed", rv.data)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.post(
            "/playlist/" + str(self.playlistid), follow_redirects=True
        )
        self.assertNotIn("updated", rv.data)
        self.assertIn("Missing", rv.data)
        self.assertEqual(Playlist[self.playlistid].name, "Playlist!")

        rv = self.client.post(
            "/playlist/" + str(self.playlistid),
            data={"name": "abc", "public": True},
            follow_redirects=True,
        )
        self.assertIn("updated", rv.data)
        self.assertNotIn("not allowed", rv.data)
        playlist = Playlist[self.playlistid]
        self.assertEqual(playlist.name, "abc")
        self.assertTrue(playlist.public)

    def test_delete(self):
        self._login("bob", "B0b")
        rv = self.client.get("/playlist/del/string", follow_redirects=True)
        self.assertIn("Invalid", rv.data)
        rv = self.client.get(
            "/playlist/del/" + str(uuid.uuid4()), follow_redirects=True
        )
        self.assertIn("Unknown", rv.data)
        rv = self.client.get(
            "/playlist/del/" + str(self.playlistid), follow_redirects=True
        )
        self.assertIn("not allowed", rv.data)
        self.assertEqual(Playlist.select().count(), 1)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.get(
            "/playlist/del/" + str(self.playlistid), follow_redirects=True
        )
        self.assertIn("deleted", rv.data)
        self.assertEqual(Playlist.select().count(), 0)


if __name__ == "__main__":
    unittest.main()

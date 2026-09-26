# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from supysonic.db.models import Album, Artist, ClientPrefs, Folder, Track, User

from ..testbase import TestBase
from . import fakes


class ScrobblerIntegrationTestCase(TestBase):
    """Checks a scrobbler gets everything it's meant to from the app layer.

    Uses the fake scrobbler rather than a real one so it stays about the
    plumbing: loading, blueprint registration, the profile page fragment and
    being handed what the API endpoint knows.
    """

    __with_webui__ = True
    __with_api__ = True
    __sections__ = {"webapp": {"scrobblers": fakes.__name__}}

    def setUp(self):
        super().setUp()

        root = Folder.create(name="Root", root=True, path="tests")
        folder = Folder.create(
            name="Folder", root=False, path="tests/assets", parent=root
        )
        artist = Artist.create(name="Artist")
        album = Album.create(name="Album", artist=artist)
        self.track = Track.create(
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

        self.user = User.get(name="alice")
        ClientPrefs.create(user=self.user, client_name="tests")

        (self.scrobbler,) = self._app_layer.scrobblers

        self._patch_client()
        self.client.post(
            "/user/login",
            data={"user": "alice", "password": "Alic3"},
            follow_redirects=True,
        )

    def _api(self, **args):
        return self.client.get(
            "/rest/scrobble.view",
            query_string={
                "u": "alice",
                "p": "Alic3",
                "c": "tests",
                "v": "1.9.0",
                "id": str(self.track.id),
                **args,
            },
        )

    def test_loaded_on_the_app_layer(self):
        self.assertIsInstance(self.scrobbler, fakes.FakeScrobbler)

    def test_blueprint_is_registered(self):
        rv = self.client.get("/scrobbler/fake/me/whoami")

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.data, "alice")

    def test_routes_require_a_login(self):
        # A scrobbler's routes act on an account, so they get the frontend's
        # login check even though they're on a blueprint of their own
        self.client.get("/user/logout")
        rv = self.client.get("/scrobbler/fake/me/whoami", follow_redirects=True)

        self.assertIn("Please login", rv.data)
        self.assertNotIn("alice", rv.data)

    def test_profile_page_includes_the_fragment(self):
        rv = self.client.get("/user/me")

        self.assertIn("fake fragment for alice", rv.data)

    def test_scrobbled_through(self):
        self._api(time=1234000)

        ((user, track, ts, client),) = self.scrobbler.scrobbled
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(track.id, self.track.id)
        self.assertEqual(ts, 1234)
        self.assertEqual(client, "tests")
        self.assertEqual(self.scrobbler.playing, [])

    def test_now_playing_through(self):
        self._api(submission="false")

        ((user, track, client),) = self.scrobbler.playing
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(track.id, self.track.id)
        self.assertEqual(client, "tests")
        self.assertEqual(self.scrobbler.scrobbled, [])


if __name__ == "__main__":
    unittest.main()

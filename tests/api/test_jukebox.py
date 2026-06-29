# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import sys
import unittest
import uuid

from threading import Thread
from time import sleep

from supysonic.daemon.server import Daemon
from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase


class JukeboxTestCase(ApiTestBase):
    def test_forbidden(self):
        # bob is neither admin nor allowed to use the jukebox
        self._make_request(
            "jukeboxControl",
            {"u": "bob", "p": "B0b", "action": "status"},
            error=50,
        )

    def test_unavailable(self):
        # No daemon running
        self._make_request("jukeboxControl", {"action": "status"}, error=0)

    def test_unknown_action(self):
        self._make_request("jukeboxControl", {"action": "frobnicate"}, error=0)

    def test_missing_parameters(self):
        # These checks happen before the daemon is contacted
        self._make_request("jukeboxControl", {"action": "skip"}, error=10)
        self._make_request("jukeboxControl", {"action": "add"}, error=10)
        self._make_request("jukeboxControl", {"action": "remove"}, error=10)
        self._make_request("jukeboxControl", {"action": "setGain"}, error=10)


class JukeboxWithDaemonTestCase(ApiTestBase):
    def setUp(self):
        super().setUp()

        # A harmless, cross-platform command that just keeps running until
        # terminated; %path/%offset are not used so nothing has to be quoted.
        self.config.DAEMON["jukebox_command"] = (
            f'"{sys.executable}" -c "import time;time.sleep(30)"'
        )

        root = Folder.create(name="Root", root=True, path="tests")
        folder = Folder.create(
            name="Folder", root=False, path="tests/assets", parent=root
        )
        artist = Artist.create(name="Artist")
        album = Album.create(name="Album", artist=artist)

        self.trackids = []
        for i in range(3):
            track = Track.create(
                title=f"Track {i}",
                album=album,
                artist=artist,
                disc=1,
                number=i + 1,
                path=f"tests/assets/track{i}",
                folder=folder,
                root_folder=root,
                duration=2,
                bitrate=320,
                last_modification=0,
            )
            self.trackids.append(str(track.id))

        self._daemon = Daemon(self.config)
        self._thread = Thread(target=self._daemon.run)
        self._thread.start()
        sleep(0.2)  # Wait a bit for the daemon thread to initialize

    def tearDown(self):
        self._daemon.terminate()
        self._thread.join()

        super().tearDown()

    def test_status_empty(self):
        rv, child = self._make_request(
            "jukeboxControl", {"action": "status"}, tag="jukeboxStatus"
        )
        self.assertEqual(child.get("currentIndex"), "0")
        self.assertEqual(child.get("playing"), "false")
        self.assertEqual(child.get("gain"), "1.0")
        self.assertEqual(child.get("position"), "0")

    def test_set_and_get(self):
        self._make_request(
            "jukeboxControl",
            {"action": "set", "id": self.trackids},
            tag="jukeboxStatus",
            skip_post=True,
        )

        rv, child = self._make_request(
            "jukeboxControl", {"action": "get"}, tag="jukeboxPlaylist"
        )
        self.assertEqual(len(child), len(self.trackids))
        self.assertEqual({e.get("id") for e in child}, set(self.trackids))

    def test_get_skips_missing_tracks(self):
        self._make_request(
            "jukeboxControl",
            {"action": "set", "id": self.trackids},
            tag="jukeboxStatus",
            skip_post=True,
        )

        # Remove a track from the DB; its path stays in the jukebox playlist
        # but can no longer be resolved back to a Track
        Track.get_by_id(uuid.UUID(self.trackids[0])).delete_instance()

        rv, child = self._make_request(
            "jukeboxControl", {"action": "get"}, tag="jukeboxPlaylist"
        )
        self.assertEqual(len(child), len(self.trackids) - 1)
        self.assertNotIn(self.trackids[0], {e.get("id") for e in child})

    def test_add_remove_clear(self):
        self._make_request(
            "jukeboxControl",
            {"action": "add", "id": self.trackids[0]},
            tag="jukeboxStatus",
            skip_post=True,
        )
        rv, child = self._make_request(
            "jukeboxControl", {"action": "get"}, tag="jukeboxPlaylist"
        )
        self.assertEqual(len(child), 1)

        self._make_request(
            "jukeboxControl",
            {"action": "remove", "index": 0},
            tag="jukeboxStatus",
            skip_post=True,
        )
        self._make_request(
            "jukeboxControl", {"action": "clear"}, tag="jukeboxStatus", skip_post=True
        )
        rv, child = self._make_request(
            "jukeboxControl", {"action": "get"}, tag="jukeboxPlaylist"
        )
        self.assertEqual(len(child), 0)

    def test_shuffle(self):
        self._make_request(
            "jukeboxControl",
            {"action": "set", "id": self.trackids},
            tag="jukeboxStatus",
            skip_post=True,
        )
        self._make_request(
            "jukeboxControl", {"action": "shuffle"}, tag="jukeboxStatus", skip_post=True
        )

        # Shuffling reorders but doesn't lose or duplicate tracks
        rv, child = self._make_request(
            "jukeboxControl", {"action": "get"}, tag="jukeboxPlaylist"
        )
        self.assertEqual({e.get("id") for e in child}, set(self.trackids))

    def test_setgain(self):
        rv, child = self._make_request(
            "jukeboxControl",
            {"action": "setGain", "gain": 0.5},
            tag="jukeboxStatus",
            skip_post=True,
        )
        self.assertEqual(child.get("gain"), "1.0")

    def test_skip(self):
        self._make_request(
            "jukeboxControl",
            {"action": "set", "id": self.trackids},
            tag="jukeboxStatus",
            skip_post=True,
        )
        rv, child = self._make_request(
            "jukeboxControl",
            {"action": "skip", "index": 0},
            tag="jukeboxStatus",
            skip_post=True,
        )
        # Skipping selects the track and starts playback
        self.assertEqual(child.get("currentIndex"), "0")
        self.assertEqual(child.get("playing"), "true")

    def test_skip_with_offset(self):
        self._make_request(
            "jukeboxControl",
            {"action": "set", "id": self.trackids},
            tag="jukeboxStatus",
            skip_post=True,
        )
        rv, child = self._make_request(
            "jukeboxControl",
            {"action": "skip", "index": 0, "offset": 5},
            tag="jukeboxStatus",
            skip_post=True,
        )
        self.assertEqual(child.get("currentIndex"), "0")
        self.assertEqual(child.get("playing"), "true")
        # The offset is accepted but not reflected in the reported position:
        # start() resets it to 0 when playback isn't already running
        self.assertEqual(child.get("position"), "0")


if __name__ == "__main__":
    unittest.main()

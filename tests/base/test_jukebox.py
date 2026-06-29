# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import uuid

from time import sleep
from unittest.mock import patch, MagicMock

from supysonic.db import Folder, Artist, Album, Track
from supysonic.jukebox import Jukebox

from ..testbase import TestBase


class JukeboxTestCase(TestBase):
    def setUp(self):
        super().setUp()

        root = Folder.create(name="Root", root=True, path="tests")
        folder = Folder.create(
            name="Folder", root=False, path="tests/assets", parent=root
        )
        artist = Artist.create(name="Artist")
        album = Album.create(name="Album", artist=artist)

        self.tracks = []
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
            self.tracks.append(track)

        self.ids = [t.id for t in self.tracks]
        self.paths = [t.path for t in self.tracks]

        self.jukebox = Jukebox("cmd %path %offset")

    def tearDown(self):
        # Make sure no playback thread is left running before the DB is dropped
        self.jukebox.terminate()
        super().tearDown()

    def test_add_resolves_paths(self):
        self.jukebox.add(self.ids[0], self.ids[1])
        self.assertEqual(self.jukebox.playlist, [self.paths[0], self.paths[1]])

        # Unknown ids are silently ignored
        self.jukebox.add(uuid.uuid4())
        self.assertEqual(self.jukebox.playlist, [self.paths[0], self.paths[1]])

    def test_set_replaces(self):
        self.jukebox.add(self.ids[0], self.ids[1])
        self.jukebox.set(self.ids[2])
        self.assertEqual(self.jukebox.playlist, [self.paths[2]])
        self.assertEqual(self.jukebox.index, 0)

    def test_clear(self):
        self.jukebox.add(*self.ids)
        self.jukebox.clear()
        self.assertEqual(self.jukebox.playlist, [])
        self.assertEqual(self.jukebox.index, 0)

    def test_remove(self):
        self.jukebox.add(*self.ids)
        self.jukebox.remove(1)
        self.assertEqual(self.jukebox.playlist, [self.paths[0], self.paths[2]])

        # Out-of-range removal is a no-op
        self.jukebox.remove(42)
        self.assertEqual(self.jukebox.playlist, [self.paths[0], self.paths[2]])

    @patch("supysonic.jukebox.Popen")
    def test_remove_adjusts_index(self, Popen):
        # skip() starts playback, so the subprocess must be mocked to keep this
        # test from spawning a real process (and failing cross-platform)
        proc = MagicMock()
        proc.poll.return_value = None
        Popen.return_value = proc

        self.jukebox.add(*self.ids)
        self.jukebox.skip(2, 0)
        self.assertEqual(self.jukebox.index, 2)

        # Removing an item before the current index shifts it down
        self.jukebox.remove(0)
        self.assertEqual(self.jukebox.index, 1)

    def test_shuffle(self):
        self.jukebox.add(*self.ids)
        self.jukebox.shuffle()
        self.assertEqual(sorted(self.jukebox.playlist), sorted(self.paths))

    def test_skip_bounds(self):
        self.jukebox.add(*self.ids)
        with self.assertRaises(IndexError):
            self.jukebox.skip(-1, 0)
        with self.assertRaises(IndexError):
            self.jukebox.skip(len(self.ids), 0)
        with self.assertRaises(ValueError):
            self.jukebox.skip(0, -1)

    def test_gain_and_setgain_noop(self):
        self.assertEqual(self.jukebox.gain, 1.0)
        self.jukebox.setgain(0.5)
        self.assertEqual(self.jukebox.gain, 1.0)

    def test_position_zero_when_stopped(self):
        self.assertEqual(self.jukebox.position, 0)
        self.assertFalse(self.jukebox.playing)

    def test_stop_when_not_playing(self):
        # No-op, must not raise
        self.jukebox.stop()
        self.assertFalse(self.jukebox.playing)

    def test_playlist_returns_copy(self):
        self.jukebox.add(*self.ids)
        playlist = self.jukebox.playlist
        playlist.append("injected")
        self.assertEqual(self.jukebox.playlist, self.paths)


@patch("supysonic.jukebox.Popen")
class JukeboxPlaybackTestCase(TestBase):
    """Tests that exercise the playback thread with a mocked subprocess."""

    def setUp(self):
        super().setUp()

        root = Folder.create(name="Root", root=True, path="tests")
        folder = Folder.create(
            name="Folder", root=False, path="tests/assets", parent=root
        )
        artist = Artist.create(name="Artist")
        album = Album.create(name="Album", artist=artist)

        self.tracks = []
        for i in range(2):
            self.tracks.append(
                Track.create(
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
            )
        self.track = self.tracks[0]

        self.jukebox = Jukebox("cmd %path %offset")

    def tearDown(self):
        self.jukebox.terminate()
        super().tearDown()

    @staticmethod
    def _make_proc():
        proc = MagicMock()
        proc.poll.return_value = None  # still running
        return proc

    def _wait_until(self, predicate, attempts=20):
        """Poll the (timing-dependent) predicate and return its final value."""
        for _ in range(attempts):
            result = predicate()
            if result:
                return result
            sleep(0.05)
        return predicate()

    def test_play_command_substitution(self, Popen):
        Popen.return_value = self._make_proc()

        self.jukebox.add(self.track.id)
        self.jukebox.start()

        # Wait for the playback thread to spawn the process
        self.assertTrue(self._wait_until(lambda: Popen.called))

        # %path is substituted; %offset is 0 for a fresh start
        args = Popen.call_args.args[0]
        self.assertEqual(args, ["cmd", self.track.path, "0"])

    def test_skip_while_playing_substitutes_offset(self, Popen):
        Popen.return_value = self._make_proc()

        self.jukebox.add(self.track.id)
        self.jukebox.start()
        self.assertTrue(self._wait_until(lambda: Popen.called))

        # Skipping while already playing keeps the requested offset and
        # respawns the process with %offset substituted
        self.jukebox.skip(0, 5)
        self.assertTrue(self._wait_until(lambda: Popen.call_count >= 2))
        self.assertEqual(Popen.call_args.args[0], ["cmd", self.track.path, "5"])

    def test_start_stop_lifecycle(self, Popen):
        Popen.return_value = self._make_proc()

        self.jukebox.add(self.track.id)
        self.jukebox.start()

        self.assertTrue(self._wait_until(lambda: self.jukebox.playing))

        self.jukebox.terminate()
        self.assertFalse(self.jukebox.playing)

    def test_skip_starts_playback(self, Popen):
        Popen.return_value = self._make_proc()

        self.jukebox.add(self.track.id)
        self.jukebox.skip(0, 0)
        self.assertEqual(self.jukebox.index, 0)

        self.assertTrue(self._wait_until(lambda: self.jukebox.playing))

    def test_stop_while_playing(self, Popen):
        Popen.return_value = self._make_proc()

        self.jukebox.add(self.track.id)
        self.jukebox.start()
        self.assertTrue(self._wait_until(lambda: self.jukebox.playing))

        self.jukebox.stop()
        self.assertTrue(self._wait_until(lambda: not self.jukebox.playing))

    def test_advances_to_next_track(self, Popen):
        # poll() returning a value means the process has finished, so the
        # playback thread should advance through the playlist and then stop
        proc = MagicMock()
        proc.poll.return_value = 0
        Popen.return_value = proc

        self.jukebox.add(*[t.id for t in self.tracks])
        self.jukebox.start()

        self.assertTrue(
            self._wait_until(lambda: not self.jukebox.playing, attempts=40)
        )
        self.assertEqual(Popen.call_count, len(self.tracks))

    def test_play_file_handles_popen_failure(self, Popen):
        # A failing play command is logged and yields no process
        Popen.side_effect = OSError("boom")

        self.jukebox.add(self.track.id)
        with self.assertLogs("supysonic.jukebox", level="ERROR"):
            proc = self.jukebox._Jukebox__play_file()
        self.assertIsNone(proc)


if __name__ == "__main__":
    unittest.main()

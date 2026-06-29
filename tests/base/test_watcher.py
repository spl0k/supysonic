# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import mutagen
import os
import shutil
import tempfile
import time
import unittest

from hashlib import sha1

from supysonic.db import init_database, release_database, Track, Artist, Folder
from supysonic.managers.folder import FolderManager
from supysonic.watcher import SupysonicWatcher

from ..testbase import TestConfig


class WatcherTestConfig(TestConfig):
    DAEMON = {"wait_delay": 0.5, "log_file": "/dev/null", "log_level": "DEBUG"}

    def __init__(self, db_uri):
        super().__init__(False, False)
        self.BASE["database_uri"] = db_uri


class WatcherTestBase(unittest.TestCase):
    def setUp(self):
        self.__db = tempfile.mkstemp()
        dburi = "sqlite:///" + self.__db[1]
        init_database(dburi)

        conf = WatcherTestConfig(dburi)
        self.__watcher = SupysonicWatcher(conf)

    def tearDown(self):
        release_database()
        os.close(self.__db[0])
        os.remove(self.__db[1])

    def _start(self):
        self.__watcher.start()
        self._wait_for(lambda: self.__watcher.running)

    def _stop(self):
        self.__watcher.stop()

    def _is_alive(self):
        return self.__watcher.running

    def _wait_for(self, predicate, attempts=30, interval=0.05):
        """Poll until predicate is truthy or attempts are exhausted; return its
        final value. A settled watcher typically lets this exit in ~0.55s; the
        ceiling (attempts*interval = 1.5s, the former fixed-sleep budget) is a
        safety margin and, thanks to the early exit, costs nothing on the fast
        path."""
        for _ in range(attempts):
            result = predicate()
            if result:
                return result
            time.sleep(interval)
        return predicate()

    def _processed(self):
        return self.__watcher.processed

    def _wait_settled(self, since):
        """Wait until the watcher has completed a processing batch after `since`
        and gone idle. Used for assertions that nothing (further) changed: a
        plain DB poll can't help there since the expected state already holds."""
        self._wait_for(
            lambda: self.__watcher.processed > since and self.__watcher.idle
        )


class WatcherTestCase(WatcherTestBase):
    def setUp(self):
        super().setUp()
        self.__dir = tempfile.mkdtemp()
        FolderManager.add("Folder", self.__dir)
        self._start()

    def tearDown(self):
        self._stop()
        shutil.rmtree(self.__dir)
        super().tearDown()

    @staticmethod
    def _tempname():
        with tempfile.NamedTemporaryFile() as f:
            return os.path.basename(f.name)

    def _temppath(self, suffix, depth=0):
        if depth > 0:
            dirpath = os.path.join(
                self.__dir, *(self._tempname() for _ in range(depth))
            )
            os.makedirs(dirpath)
        else:
            dirpath = self.__dir
        return os.path.join(dirpath, self._tempname() + suffix)

    def _addfile(self, depth=0):
        path = self._temppath(".mp3", depth)
        shutil.copyfile("tests/assets/folder/silence.mp3", path)
        return path

    def _addcover(self, suffix=None, depth=0):
        suffix = ".jpg" if suffix is None else (suffix + ".jpg")
        path = self._temppath(suffix, depth)
        shutil.copyfile("tests/assets/cover.jpg", path)
        return path


class AudioWatcherTestCase(WatcherTestCase):
    def assertTrackCountEqual(self, expected):
        self.assertEqual(Track.select().count(), expected)

    def assertTrackCountReaches(self, expected):
        self._wait_for(lambda: Track.select().count() == expected)
        self.assertEqual(Track.select().count(), expected)

    def test_add(self):
        self._addfile()
        self.assertTrackCountEqual(0)
        self.assertTrackCountReaches(1)

    def test_add_nowait_stop(self):
        self._addfile()
        # Add a small delay (< wait_delay) so wathdog can pick up that a file was added
        time.sleep(0.1)
        self._stop()
        self.assertTrackCountEqual(1)

    def test_add_multiple(self):
        self._addfile()
        self._addfile()
        self._addfile()
        self.assertTrackCountEqual(0)

        self.assertTrackCountReaches(3)
        self.assertEqual(Artist.select().count(), 1)

    def test_change(self):
        path = self._addfile()
        self.assertTrackCountReaches(1)

        self.assertEqual(Artist.select().where(Artist.name == "Some artist").count(), 1)
        trackid = Track.select().first().id

        tags = mutagen.File(path, easy=True)
        tags["artist"] = "Renamed"
        tags.save()
        # The scanner only rescans when the file's (integer-second) mtime is
        # strictly greater than the stored last_modification. Without the former
        # fixed sleep the edit can land in the same second as the initial scan,
        # so bump the mtime explicitly to guarantee the change is picked up.
        st = os.stat(path)
        os.utime(path, (st.st_atime, st.st_mtime + 2))
        # The now-orphaned "Some artist" is only dropped once the rescan has
        # reassigned the track AND scanner.prune() has run, so poll on that final
        # state. Polling for "Renamed" would race: it is created mid-scan, before
        # prune.
        self._wait_for(
            lambda: Artist.select().where(Artist.name == "Some artist").count() == 0
        )

        self.assertEqual(Track.select().count(), 1)
        self.assertEqual(Artist.select().where(Artist.name == "Some artist").count(), 0)
        self.assertEqual(Artist.select().where(Artist.name == "Renamed").count(), 1)
        self.assertEqual(Track.select().first().id, trackid)

    def test_rename(self):
        path = self._addfile()
        self.assertTrackCountReaches(1)
        trackid = Track.select().first().id

        newpath = self._temppath(".mp3")
        shutil.move(path, newpath)
        self._wait_for(
            lambda: getattr(Track.select().first(), "path", None) == newpath
        )

        track = Track.select().first()
        self.assertIsNotNone(track)
        self.assertNotEqual(track.path, path)
        self.assertEqual(track.path, newpath)
        self.assertEqual(
            track._path_hash, memoryview(sha1(newpath.encode("utf-8")).digest())
        )
        self.assertEqual(track.id, trackid)

    def test_move_in(self):
        filename = self._tempname() + ".mp3"
        initialpath = os.path.join(tempfile.gettempdir(), filename)
        shutil.copyfile("tests/assets/folder/silence.mp3", initialpath)
        shutil.move(initialpath, self._temppath(".mp3"))
        self.assertTrackCountReaches(1)

    def test_move_out(self):
        initialpath = self._addfile()
        self.assertTrackCountReaches(1)

        newpath = os.path.join(tempfile.gettempdir(), os.path.basename(initialpath))
        shutil.move(initialpath, newpath)
        self.assertTrackCountReaches(0)

        os.unlink(newpath)

    def test_delete(self):
        path = self._addfile()
        self.assertTrackCountReaches(1)

        os.unlink(path)
        self.assertTrackCountReaches(0)

    def test_add_delete(self):
        before = self._processed()
        path = self._addfile()
        os.unlink(path)
        self._wait_settled(before)
        self.assertTrackCountEqual(0)

    def test_add_rename(self):
        path = self._addfile()
        shutil.move(path, self._temppath(".mp3"))
        self.assertTrackCountReaches(1)

    def test_rename_delete(self):
        path = self._addfile()
        self.assertTrackCountReaches(1)

        newpath = self._temppath(".mp3")
        shutil.move(path, newpath)
        os.unlink(newpath)
        self.assertTrackCountReaches(0)

    def test_add_rename_delete(self):
        before = self._processed()
        path = self._addfile()
        newpath = self._temppath(".mp3")
        shutil.move(path, newpath)
        os.unlink(newpath)
        self._wait_settled(before)
        self.assertTrackCountEqual(0)

    def test_rename_rename(self):
        path = self._addfile()
        self.assertTrackCountReaches(1)

        before = self._processed()
        newpath = self._temppath(".mp3")
        finalpath = self._temppath(".mp3")
        shutil.move(path, newpath)
        shutil.move(newpath, finalpath)
        self._wait_settled(before)
        self.assertTrackCountEqual(1)


class CoverWatcherTestCase(WatcherTestCase):
    def _cover(self):
        folder = Folder.select().first()
        return folder.cover_art if folder is not None else None

    def assertCoverReaches(self, expected):
        self._wait_for(lambda: self._cover() == expected)
        self.assertEqual(self._cover(), expected)

    def test_add_file_then_cover(self):
        self._addfile()
        path = self._addcover()
        self.assertCoverReaches(os.path.basename(path))

    def test_add_cover_then_file(self):
        path = self._addcover()
        self._addfile()
        self.assertCoverReaches(os.path.basename(path))

    def test_remove_cover(self):
        self._addfile()
        path = self._addcover()
        self.assertCoverReaches(os.path.basename(path))

        os.unlink(path)
        self.assertCoverReaches(None)

    def test_naming_add_good(self):
        bad = os.path.basename(self._addcover())
        self.assertCoverReaches(bad)
        good = os.path.basename(self._addcover("cover"))
        self.assertCoverReaches(good)

    def test_naming_add_bad(self):
        good = os.path.basename(self._addcover("cover"))
        self.assertCoverReaches(good)

        before = self._processed()
        self._addcover()
        self._wait_settled(before)
        self.assertEqual(self._cover(), good)

    def test_naming_remove_good(self):
        bad = self._addcover()
        good = self._addcover("cover")
        self.assertCoverReaches(os.path.basename(good))
        os.unlink(good)
        self.assertCoverReaches(os.path.basename(bad))

    def test_naming_remove_bad(self):
        bad = self._addcover()
        good = self._addcover("cover")
        self.assertCoverReaches(os.path.basename(good))

        before = self._processed()
        os.unlink(bad)
        self._wait_settled(before)
        self.assertEqual(self._cover(), os.path.basename(good))

    def test_rename(self):
        path = self._addcover()
        self.assertCoverReaches(os.path.basename(path))
        newpath = self._temppath(".jpg")
        shutil.move(path, newpath)
        self.assertCoverReaches(os.path.basename(newpath))

    def test_add_to_folder_without_track(self):
        before = self._processed()
        path = self._addcover(depth=1)
        self._wait_settled(before)

        self.assertFalse(
            Folder.select().where(Folder.cover_art == os.path.basename(path)).exists()
        )

    def test_remove_from_folder_without_track(self):
        before = self._processed()
        path = self._addcover(depth=1)
        self._wait_settled(before)

        before = self._processed()
        os.unlink(path)
        self._wait_settled(before)

    def test_add_track_to_empty_folder(self):
        before = self._processed()
        self._addfile(1)
        self._wait_settled(before)


if __name__ == "__main__":
    unittest.main()

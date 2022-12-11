# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2022 Alban 'spl0k' Féron
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
        self.__sleep_time = conf.DAEMON["wait_delay"] + 1

        self.__watcher = SupysonicWatcher(conf)

    def tearDown(self):
        release_database()
        os.close(self.__db[0])
        os.remove(self.__db[1])

    def _start(self):
        self.__watcher.start()
        time.sleep(0.2)

    def _stop(self):
        self.__watcher.stop()

    def _is_alive(self):
        return self.__watcher.running

    def _sleep(self):
        time.sleep(self.__sleep_time)


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

    def test_add(self):
        self._addfile()
        self.assertTrackCountEqual(0)
        self._sleep()
        self.assertTrackCountEqual(1)

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
        self._sleep()

        self.assertEqual(Track.select().count(), 3)
        self.assertEqual(Artist.select().count(), 1)

    def test_change(self):
        path = self._addfile()
        self._sleep()

        trackid = None
        self.assertEqual(Track.select().count(), 1)
        self.assertEqual(Artist.select().where(Artist.name == "Some artist").count(), 1)
        trackid = Track.select().first().id

        tags = mutagen.File(path, easy=True)
        tags["artist"] = "Renamed"
        tags.save()
        self._sleep()

        self.assertEqual(Track.select().count(), 1)
        self.assertEqual(Artist.select().where(Artist.name == "Some artist").count(), 0)
        self.assertEqual(Artist.select().where(Artist.name == "Renamed").count(), 1)
        self.assertEqual(Track.select().first().id, trackid)

    def test_rename(self):
        path = self._addfile()
        self._sleep()

        trackid = None
        self.assertEqual(Track.select().count(), 1)
        trackid = Track.select().first().id

        newpath = self._temppath(".mp3")
        shutil.move(path, newpath)
        self._sleep()

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
        self._sleep()
        self.assertTrackCountEqual(1)

    def test_move_out(self):
        initialpath = self._addfile()
        self._sleep()
        self.assertTrackCountEqual(1)

        newpath = os.path.join(tempfile.gettempdir(), os.path.basename(initialpath))
        shutil.move(initialpath, newpath)
        self._sleep()
        self.assertTrackCountEqual(0)

        os.unlink(newpath)

    def test_delete(self):
        path = self._addfile()
        self._sleep()
        self.assertTrackCountEqual(1)

        os.unlink(path)
        self._sleep()
        self.assertTrackCountEqual(0)

    def test_add_delete(self):
        path = self._addfile()
        os.unlink(path)
        self._sleep()
        self.assertTrackCountEqual(0)

    def test_add_rename(self):
        path = self._addfile()
        shutil.move(path, self._temppath(".mp3"))
        self._sleep()
        self.assertTrackCountEqual(1)

    def test_rename_delete(self):
        path = self._addfile()
        self._sleep()
        self.assertTrackCountEqual(1)

        newpath = self._temppath(".mp3")
        shutil.move(path, newpath)
        os.unlink(newpath)
        self._sleep()
        self.assertTrackCountEqual(0)

    def test_add_rename_delete(self):
        path = self._addfile()
        newpath = self._temppath(".mp3")
        shutil.move(path, newpath)
        os.unlink(newpath)
        self._sleep()
        self.assertTrackCountEqual(0)

    def test_rename_rename(self):
        path = self._addfile()
        self._sleep()
        self.assertTrackCountEqual(1)

        newpath = self._temppath(".mp3")
        finalpath = self._temppath(".mp3")
        shutil.move(path, newpath)
        shutil.move(newpath, finalpath)
        self._sleep()
        self.assertTrackCountEqual(1)


class CoverWatcherTestCase(WatcherTestCase):
    def test_add_file_then_cover(self):
        self._addfile()
        path = self._addcover()
        self._sleep()

        self.assertEqual(Folder.select().first().cover_art, os.path.basename(path))

    def test_add_cover_then_file(self):
        path = self._addcover()
        self._addfile()
        self._sleep()

        self.assertEqual(Folder.select().first().cover_art, os.path.basename(path))

    def test_remove_cover(self):
        self._addfile()
        path = self._addcover()
        self._sleep()

        os.unlink(path)
        self._sleep()

        self.assertIsNone(Folder.select().first().cover_art)

    def test_naming_add_good(self):
        self._addcover()
        self._sleep()
        good = os.path.basename(self._addcover("cover"))
        self._sleep()

        self.assertEqual(Folder.select().first().cover_art, good)

    def test_naming_add_bad(self):
        good = os.path.basename(self._addcover("cover"))
        self._sleep()
        self._addcover()
        self._sleep()

        self.assertEqual(Folder.select().first().cover_art, good)

    def test_naming_remove_good(self):
        bad = self._addcover()
        good = self._addcover("cover")
        self._sleep()
        os.unlink(good)
        self._sleep()

        self.assertEqual(Folder.select().first().cover_art, os.path.basename(bad))

    def test_naming_remove_bad(self):
        bad = self._addcover()
        good = self._addcover("cover")
        self._sleep()
        os.unlink(bad)
        self._sleep()

        self.assertEqual(Folder.select().first().cover_art, os.path.basename(good))

    def test_rename(self):
        path = self._addcover()
        self._sleep()
        newpath = self._temppath(".jpg")
        shutil.move(path, newpath)
        self._sleep()

        self.assertEqual(Folder.select().first().cover_art, os.path.basename(newpath))

    def test_add_to_folder_without_track(self):
        path = self._addcover(depth=1)
        self._sleep()

        self.assertFalse(
            Folder.select().where(Folder.cover_art == os.path.basename(path)).exists()
        )

    def test_remove_from_folder_without_track(self):
        path = self._addcover(depth=1)
        self._sleep()
        os.unlink(path)
        self._sleep()

    def test_add_track_to_empty_folder(self):
        self._addfile(1)
        self._sleep()


if __name__ == "__main__":
    unittest.main()

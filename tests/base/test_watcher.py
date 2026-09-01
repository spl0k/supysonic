# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import itertools
import os
import shutil
import tempfile
import time
import unittest
from hashlib import sha1
from unittest.mock import Mock, patch

import mediafile
from watchdog.events import FileCreatedEvent

from supysonic.db import Artist, Folder, Track, init_database
from supysonic.managers.folder import FolderManager
from supysonic.watcher import (
    FLAG_COVER,
    FLAG_CREATE,
    OP_MOVE,
    OP_REMOVE,
    OP_SCAN,
    Event,
    ScannerProcessingQueue,
    SupysonicWatcher,
    SupysonicWatcherEventHandler,
)

from ..testbase import TestConfig, get_test_db_uri, teardown_test_db


class WatcherTestConfig(TestConfig):
    DAEMON = {
        "wait_delay": 0.5,
        "log_file": "/dev/null",
        "log_level": "DEBUG",
        "socket": None,
    }

    def __init__(self, db_uri):
        super().__init__(False, False)
        self.BASE["database_uri"] = db_uri


class WatcherTestBase(unittest.TestCase):
    def setUp(self):
        dburi, self.__db = get_test_db_uri()
        init_database(dburi)

        conf = WatcherTestConfig(dburi)
        self.__watcher = SupysonicWatcher(conf)

    def tearDown(self):
        teardown_test_db(self.__db)

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
        self._wait_for(lambda: self.__watcher.processed > since and self.__watcher.idle)


class WatcherTestCase(WatcherTestBase):
    def setUp(self):
        super().setUp()
        self.__dir = tempfile.mkdtemp()
        FolderManager().add("Folder", self.__dir)
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

        tags = mediafile.MediaFile(path)
        tags.artist = "Renamed"
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
        self._wait_for(lambda: getattr(Track.select().first(), "path", None) == newpath)

        track = Track.select().first()
        self.assertIsNotNone(track)
        self.assertNotEqual(track.path, path)
        self.assertEqual(track.path, newpath)
        # bytes() normalizes what each driver returns for a blob column: psycopg2
        # hands back a memoryview of format 'c', which never compares equal to one
        # of format 'B' however identical the underlying bytes are
        self.assertEqual(
            bytes(track._path_hash), sha1(newpath.encode("utf-8")).digest()
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


class WatcherUnitTestCase(unittest.TestCase):
    """Unit-level branches of the watcher that need neither the OS observer
    nor a running processing thread."""

    def test_event_handler_with_extensions(self):
        handler = SupysonicWatcherEventHandler("mp3 ogg")
        self.assertIsNotNone(handler)

    def test_put_after_stop_raises(self):
        queue = ScannerProcessingQueue(60)
        queue.stop()
        self.assertRaises(RuntimeError, queue.put, "/some/path.mp3", OP_SCAN)

    def test_unschedule_paths(self):
        queue = ScannerProcessingQueue(60)
        queue.put("/music/a.mp3", OP_SCAN)
        queue.put("/music/sub/b.mp3", OP_SCAN)
        queue.put("/other/c.mp3", OP_SCAN)
        # a mere string prefix isn't inside "/music"
        queue.put("/music2/d.mp3", OP_SCAN)
        queue.unschedule_paths("/music")
        remaining = queue._ScannerProcessingQueue__path_to_item
        self.assertEqual(set(remaining), {"/other/c.mp3", "/music2/d.mp3"})

    def test_next_item_not_yet_due(self):
        # A freshly queued item isn't returned until its debounce delay elapses.
        queue = ScannerProcessingQueue(60)
        queue.put("/music/a.mp3", OP_SCAN)
        self.assertIsNone(queue._ScannerProcessingQueue__next_item())

    @staticmethod
    def _items(queue):
        return queue._ScannerProcessingQueue__items

    @staticmethod
    def _paths(queue):
        return queue._ScannerProcessingQueue__path_to_item

    def _assertQueueConsistent(self, queue):
        """The queue holds its events sorted by time, exactly once each, and
        __path_to_item mirrors __items. Anything mutating an event's time while
        it sits in __items breaks the ordering these invariants rest on."""

        items = self._items(queue)
        times = [i.time for i in items]
        self.assertEqual(times, sorted(times), "__items isn't sorted by time")
        self.assertEqual(len({id(i) for i in items}), len(items), "duplicate events")
        self.assertEqual(self._paths(queue), {i.path: i for i in items})

    def test_put_existing_path_is_reinserted(self):
        # Re-queuing a pending path moves its event to the tail. set() bumps the
        # event's time, which is the very key __items is ordered on, so the event
        # has to leave the list before being updated.
        queue = ScannerProcessingQueue(60)
        # a distinct time per event, whatever the platform clock resolution
        with patch("supysonic.watcher.time.monotonic", side_effect=itertools.count()):
            for path in ("/music/a.mp3", "/music/b.mp3", "/music/c.mp3"):
                queue.put(path, OP_SCAN)
            queue.put("/music/a.mp3", OP_SCAN)
            queue.put("/music/b.mp3", OP_SCAN | FLAG_CREATE)
            queue.put("/music/a.mp3", OP_REMOVE)

        self._assertQueueConsistent(queue)
        self.assertEqual(
            [i.path for i in self._items(queue)],
            ["/music/c.mp3", "/music/b.mp3", "/music/a.mp3"],
        )
        # the last operation on a path wins, SCAN and REMOVE being exclusive
        self.assertEqual(self._paths(queue)["/music/a.mp3"].operation, OP_REMOVE)

    def test_put_existing_path_unpatched_clock(self):
        # Same, on the real clock: the breakage used to hide whenever duplicate
        # events happened to land within a single monotonic tick.
        queue = ScannerProcessingQueue(60)
        for path in ("/music/a.mp3", "/music/b.mp3", "/music/c.mp3"):
            queue.put(path, OP_SCAN)
        for _ in range(200):
            queue.put("/music/a.mp3", OP_SCAN)
            queue.put("/music/c.mp3", OP_SCAN)

        self._assertQueueConsistent(queue)
        self.assertEqual(len(self._items(queue)), 3)

    def test_put_move_merges_source_event(self):
        # Moving a file with a pending event folds that event into the one for
        # the destination, and forgets the source path.
        queue = ScannerProcessingQueue(60)
        queue.put("/music/src.mp3", OP_SCAN)
        queue.put("/music/dst.mp3", OP_MOVE, src_path="/music/src.mp3")

        self._assertQueueConsistent(queue)
        self.assertEqual(set(self._paths(queue)), {"/music/dst.mp3"})
        event = self._paths(queue)["/music/dst.mp3"]
        self.assertTrue(event.operation & OP_MOVE)
        self.assertTrue(event.operation & OP_SCAN)
        self.assertEqual(event.src_path, "/music/src.mp3")

    def test_put_move_onto_itself(self):
        # Degenerate move where source and destination are the same pending
        # event: it must be kept, not merged into itself and dropped.
        queue = ScannerProcessingQueue(60)
        queue.put("/music/a.mp3", OP_SCAN)
        queue.put("/music/a.mp3", OP_MOVE, src_path="/music/a.mp3")

        self._assertQueueConsistent(queue)
        self.assertEqual(set(self._paths(queue)), {"/music/a.mp3"})

    def test_unschedule_paths_after_reinsertion(self):
        queue = ScannerProcessingQueue(60)
        queue.put("/music/a.mp3", OP_SCAN)
        queue.put("/music/sub/b.mp3", OP_SCAN)
        queue.put("/other/c.mp3", OP_SCAN)
        queue.put("/music/a.mp3", OP_SCAN)
        queue.unschedule_paths("/music")

        self._assertQueueConsistent(queue)
        self.assertEqual(set(self._paths(queue)), {"/other/c.mp3"})

    def test_next_item_drains_queue(self):
        # Every due event comes out exactly once, leaving the queue empty.
        queue = ScannerProcessingQueue(0)
        with patch("supysonic.watcher.time.monotonic", side_effect=itertools.count()):
            queue.put("/music/a.mp3", OP_SCAN)
            queue.put("/music/b.mp3", OP_SCAN)
            queue.put("/music/a.mp3", OP_SCAN)

            drained = []
            while (item := queue._ScannerProcessingQueue__next_item()) is not None:
                drained.append(item.path)

        self.assertEqual(drained, ["/music/b.mp3", "/music/a.mp3"])
        self.assertEqual(self._items(queue), [])
        self.assertEqual(self._paths(queue), {})

    def test_dispatch_logs_handler_errors(self):
        # A handler blowing up is logged and contained: letting it through would
        # take down the observer thread.
        handler = SupysonicWatcherEventHandler(None)
        handler.queue = Mock()
        handler.queue.put.side_effect = RuntimeError("nope")

        with self.assertLogs("supysonic.watcher", level="ERROR") as cm:
            handler.dispatch(FileCreatedEvent("/music/a.mp3"))
        self.assertIn("Error while handling filesystem event", "\n".join(cm.output))

    def test_process_cover_scan_directory(self):
        # A cover SCAN on a directory triggers a cover search for that folder.
        queue = ScannerProcessingQueue(60)
        scanner = Mock()
        with tempfile.TemporaryDirectory() as d:
            event = Event(d, OP_SCAN | FLAG_COVER)
            queue._ScannerProcessingQueue__process_cover_item(scanner, event)
        scanner.find_cover.assert_called_once_with(d)

    def test_add_remove_folder_type_error(self):
        watcher = SupysonicWatcher(WatcherTestConfig("sqlite:"))
        self.assertRaises(TypeError, watcher.add_folder, 42)
        self.assertRaises(TypeError, watcher.remove_folder, 42)

    def test_remove_folder_not_watched(self):
        # Unscheduling a folder that was never scheduled does nothing but warn
        watcher = SupysonicWatcher(WatcherTestConfig("sqlite:"))
        with self.assertLogs("supysonic.watcher", level="WARNING") as cm:
            watcher.remove_folder("/music")
        self.assertIn("No watcher scheduled for /music", "\n".join(cm.output))

    def test_add_remove_folder(self):
        watcher = SupysonicWatcher(WatcherTestConfig("sqlite:"))
        observer = Mock()
        watcher._SupysonicWatcher__observer = observer
        watcher._SupysonicWatcher__queue = Mock()

        watcher.add_folder("/music")
        watch = observer.schedule.return_value

        watcher.remove_folder("/music")
        observer.unschedule.assert_called_once_with(watch)

        # the folder is now forgotten, unscheduling it again only warns
        with self.assertLogs("supysonic.watcher", level="WARNING"):
            watcher.remove_folder("/music")
        observer.unschedule.assert_called_once_with(watch)


if __name__ == "__main__":
    unittest.main()

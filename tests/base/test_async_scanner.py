#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import io
import mutagen
import os.path
import tempfile
import unittest

from contextlib import contextmanager
from pony.orm import db_session, commit

from supysonic import db
from supysonic.managers.folder import FolderManager
from supysonic.scanner import AsyncScanner

class AsyncScannerTestCase(unittest.TestCase):
    def setUp(self):
        dbfile = tempfile.mkstemp()[1]
        db.init_database('sqlite:///' + dbfile)
        self.scanner = AsyncScanner()

        with db_session:
            folder = FolderManager.add('folder', os.path.abspath('tests/assets/folder'))
            self.assertIsNotNone(folder)
            self.folderid = folder.id
            commit()

            self.scanner.scan(folder)
            self.scanner.await_all()

    def tearDown(self):
        self.scanner.finish()
        self.scanner.shutdown()
        db.release_database()

    @contextmanager
    @db_session
    def __temporary_track_copy(self):
        track = db.Track.select().first()
        with tempfile.NamedTemporaryFile(dir = os.path.dirname(track.path)) as tf:
            with io.open(track.path, 'rb') as f:
                tf.write(f.read())
            yield tf

    @db_session
    def test_scan(self):
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_progress(self):
        callbacks = set()
        tid = self.scanner.scan(db.Folder[self.folderid], callbacks.add)
        self.scanner.await_task(tid)
        for progress in callbacks:
            self.assertIsInstance(progress, int)

    @db_session
    def test_scan_file(self):
        tid = self.scanner.scan_file('/some/inexistent/path')
        self.scanner.await_task(tid)
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_remove_file(self):
        self.scanner.remove_file('/some/inexistent/path')
        self.scanner.await_all()
        self.assertEqual(db.Track.select().count(), 1)

        track = db.Track.select().first()
        self.scanner.remove_file(track.path)
        self.scanner.finish()
        self.scanner.await_all()
        commit()
        self.assertEqual(db.Track.select().count(), 0)
        self.assertEqual(db.Album.select().count(), 0)
        self.assertEqual(db.Artist.select().count(), 0)

    def test_move_file(self):
        with db_session:
            track = db.Track.select().first()
            self.scanner.move_file('/some/inexistent/path', track.path)
            self.scanner.await_all()
            self.assertEqual(db.Track.select().count(), 1)

            self.scanner.move_file(track.path, track.path)
            self.scanner.await_all()
            self.assertEqual(db.Track.select().count(), 1)

        with self.__temporary_track_copy() as tf:
            with db_session:
                self.scanner.scan(db.Folder[self.folderid])
                self.scanner.await_all()
                self.assertEqual(db.Track.select().count(), 2)
            with db_session:
                self.scanner.move_file(tf.name, track.path)
                self.scanner.await_all()
                self.assertEqual(db.Track.select().count(), 1)

        with db_session:
            track = db.Track.select().first()
            new_path = track.path.replace('silence','silence_moved')
            self.scanner.move_file(track.path, new_path)
            self.scanner.await_all()
        with db_session:
            track = db.Track.select().first()
            self.assertEqual(db.Track.select().count(), 1)
            self.assertEqual(track.path, new_path)

    def test_stats(self):
        stats = self.scanner.stats()
        self.assertEqual(stats.added.artists, 1)
        self.assertEqual(stats.added.albums, 1)
        self.assertEqual(stats.added.tracks, 1)
        self.assertEqual(stats.deleted.artists, 0)
        self.assertEqual(stats.deleted.albums, 0)
        self.assertEqual(stats.deleted.tracks, 0)

    def test_shared_scanners(self):
        second_scanner = AsyncScanner()
        self.assertEqual(self.scanner._id, second_scanner._id)

    def test_replacement_scanner(self):
        old_scanner = self.scanner
        old_scanner.shutdown()
        self.scanner = AsyncScanner()
        self.assertNotEqual(self.scanner._id, old_scanner._id)
        tid = self.scanner.scan_id(self.folderid)
        self.scanner.await_task(tid)

if __name__ == '__main__':
    unittest.main()


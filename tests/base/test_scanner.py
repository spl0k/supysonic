#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import io
import mutagen
import os.path
import tempfile
import unittest

from contextlib import contextmanager

from supysonic import db
from supysonic.managers.folder import FolderManager
from supysonic.scanner import Scanner

class ScannerTestCase(unittest.TestCase):
    def setUp(self):
        self.store = db.get_store('sqlite:')
        with io.open('schema/sqlite.sql', 'r') as f:
            for statement in f.read().split(';'):
                self.store.execute(statement)

        FolderManager.add(self.store, 'folder', os.path.abspath('tests/assets'))
        self.folder = self.store.find(db.Folder).one()
        self.assertIsNotNone(self.folder)

        self.scanner = Scanner(self.store)
        self.scanner.scan(self.folder)

    def tearDown(self):
        self.scanner.finish()
        self.store.close()

    @contextmanager
    def __temporary_track_copy(self):
        track = self.store.find(db.Track).one()
        with tempfile.NamedTemporaryFile(dir = os.path.dirname(track.path)) as tf:
            with io.open(track.path, 'rb') as f:
                tf.write(f.read())
            yield tf

    def test_scan(self):
        self.assertEqual(self.store.find(db.Track).count(), 1)

        self.assertRaises(TypeError, self.scanner.scan, None)
        self.assertRaises(TypeError, self.scanner.scan, 'string')

    def test_progress(self):
        def progress(processed, total):
            self.assertIsInstance(processed, int)
            self.assertIsInstance(total, int)
            self.assertLessEqual(processed, total)

        self.scanner.scan(self.folder, progress)

    def test_rescan(self):
        self.scanner.scan(self.folder)
        self.assertEqual(self.store.find(db.Track).count(), 1)

    def test_force_rescan(self):
        self.scanner = Scanner(self.store, True)
        self.scanner.scan(self.folder)
        self.assertEqual(self.store.find(db.Track).count(), 1)

    def test_scan_file(self):
        track = self.store.find(db.Track).one()
        self.assertRaises(TypeError, self.scanner.scan_file, None)
        self.assertRaises(TypeError, self.scanner.scan_file, track)

        self.scanner.scan_file('/some/inexistent/path')
        self.assertEqual(self.store.find(db.Track).count(), 1)

    def test_remove_file(self):
        track = self.store.find(db.Track).one()
        self.assertRaises(TypeError, self.scanner.remove_file, None)
        self.assertRaises(TypeError, self.scanner.remove_file, track)

        self.scanner.remove_file('/some/inexistent/path')
        self.assertEqual(self.store.find(db.Track).count(), 1)

        self.scanner.remove_file(track.path)
        self.scanner.finish()
        self.assertEqual(self.store.find(db.Track).count(), 0)
        self.assertEqual(self.store.find(db.Album).count(), 0)
        self.assertEqual(self.store.find(db.Artist).count(), 0)

    def test_move_file(self):
        track = self.store.find(db.Track).one()
        self.assertRaises(TypeError, self.scanner.move_file, None, 'string')
        self.assertRaises(TypeError, self.scanner.move_file, track, 'string')
        self.assertRaises(TypeError, self.scanner.move_file, 'string', None)
        self.assertRaises(TypeError, self.scanner.move_file, 'string', track)

        self.scanner.move_file('/some/inexistent/path', track.path)
        self.assertEqual(self.store.find(db.Track).count(), 1)

        self.scanner.move_file(track.path, track.path)
        self.assertEqual(self.store.find(db.Track).count(), 1)

        self.assertRaises(Exception, self.scanner.move_file, track.path, '/some/inexistent/path')

        with self.__temporary_track_copy() as tf:
            self.scanner.scan(self.folder)
            self.assertEqual(self.store.find(db.Track).count(), 2)
            self.scanner.move_file(tf.name, track.path)
            self.assertEqual(self.store.find(db.Track).count(), 1)

        track = self.store.find(db.Track).one()
        new_path = os.path.abspath(os.path.join(os.path.dirname(track.path), '..', 'silence.mp3'))
        self.scanner.move_file(track.path, new_path)
        self.assertEqual(self.store.find(db.Track).count(), 1)
        self.assertEqual(track.path, new_path)

    def test_rescan_corrupt_file(self):
        track = self.store.find(db.Track).one()
        self.scanner = Scanner(self.store, True)

        with self.__temporary_track_copy() as tf:
            self.scanner.scan(self.folder)
            self.assertEqual(self.store.find(db.Track).count(), 2)

            tf.seek(0, 0)
            tf.write('\x00' * 4096)
            tf.truncate()

            self.scanner.scan(self.folder)
            self.assertEqual(self.store.find(db.Track).count(), 1)

    def test_rescan_removed_file(self):
        track = self.store.find(db.Track).one()

        with self.__temporary_track_copy() as tf:
            self.scanner.scan(self.folder)
            self.assertEqual(self.store.find(db.Track).count(), 2)

        self.scanner.scan(self.folder)
        self.assertEqual(self.store.find(db.Track).count(), 1)

    def test_scan_tag_change(self):
        self.scanner = Scanner(self.store, True)

        with self.__temporary_track_copy() as tf:
            self.scanner.scan(self.folder)
            copy = self.store.find(db.Track, db.Track.path == tf.name).one()
            self.assertEqual(copy.artist.name, 'Some artist')
            self.assertEqual(copy.album.name, 'Awesome album')

            tags = mutagen.File(copy.path, easy = True)
            tags['artist'] = 'Renamed artist'
            tags['album'] = 'Crappy album'
            tags.save()

            self.scanner.scan(self.folder)
            self.scanner.finish()
            self.assertEqual(copy.artist.name, 'Renamed artist')
            self.assertEqual(copy.album.name, 'Crappy album')
            self.assertIsNotNone(self.store.find(db.Artist, db.Artist.name == 'Some artist').one())
            self.assertIsNotNone(self.store.find(db.Album, db.Album.name == 'Awesome album').one())

    def test_stats(self):
        self.assertEqual(self.scanner.stats(), ((1,1,1),(0,0,0)))

if __name__ == '__main__':
    unittest.main()


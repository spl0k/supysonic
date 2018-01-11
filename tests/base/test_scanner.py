#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
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
from supysonic.scanner import Scanner

class ScannerTestCase(unittest.TestCase):
    def setUp(self):
        db.init_database('sqlite:', True)

        FolderManager.add('folder', os.path.abspath('tests/assets'))
        with db_session:
            folder = db.Folder.select().first()
            self.assertIsNotNone(folder)
            self.folderid = folder.id

            self.scanner = Scanner()
            self.scanner.scan(folder)

    def tearDown(self):
        self.scanner.finish()
        db.release_database()

    @contextmanager
    def __temporary_track_copy(self):
        track = db.Track.select().first()
        with tempfile.NamedTemporaryFile(dir = os.path.dirname(track.path)) as tf:
            with io.open(track.path, 'rb') as f:
                tf.write(f.read())
            yield tf

    @db_session
    def test_scan(self):
        self.assertEqual(db.Track.select().count(), 1)

        self.assertRaises(TypeError, self.scanner.scan, None)
        self.assertRaises(TypeError, self.scanner.scan, 'string')

    @db_session
    def test_progress(self):
        def progress(processed, total):
            self.assertIsInstance(processed, int)
            self.assertIsInstance(total, int)
            self.assertLessEqual(processed, total)

        self.scanner.scan(db.Folder[self.folderid], progress)

    @db_session
    def test_rescan(self):
        self.scanner.scan(db.Folder[self.folderid])
        commit()
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_force_rescan(self):
        self.scanner = Scanner(True)
        self.scanner.scan(db.Folder[self.folderid])
        commit()
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_scan_file(self):
        track = db.Track.select().first()
        self.assertRaises(TypeError, self.scanner.scan_file, None)
        self.assertRaises(TypeError, self.scanner.scan_file, track)

        self.scanner.scan_file('/some/inexistent/path')
        commit()
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_remove_file(self):
        track = db.Track.select().first()
        self.assertRaises(TypeError, self.scanner.remove_file, None)
        self.assertRaises(TypeError, self.scanner.remove_file, track)

        self.scanner.remove_file('/some/inexistent/path')
        commit()
        self.assertEqual(db.Track.select().count(), 1)

        self.scanner.remove_file(track.path)
        self.scanner.finish()
        commit()
        self.assertEqual(db.Track.select().count(), 0)
        self.assertEqual(db.Album.select().count(), 0)
        self.assertEqual(db.Artist.select().count(), 0)

    @db_session
    def test_move_file(self):
        track = db.Track.select().first()
        self.assertRaises(TypeError, self.scanner.move_file, None, 'string')
        self.assertRaises(TypeError, self.scanner.move_file, track, 'string')
        self.assertRaises(TypeError, self.scanner.move_file, 'string', None)
        self.assertRaises(TypeError, self.scanner.move_file, 'string', track)

        self.scanner.move_file('/some/inexistent/path', track.path)
        commit()
        self.assertEqual(db.Track.select().count(), 1)

        self.scanner.move_file(track.path, track.path)
        commit()
        self.assertEqual(db.Track.select().count(), 1)

        self.assertRaises(Exception, self.scanner.move_file, track.path, '/some/inexistent/path')

        with self.__temporary_track_copy() as tf:
            self.scanner.scan(db.Folder[self.folderid])
            commit()
            self.assertEqual(db.Track.select().count(), 2)
            self.scanner.move_file(tf.name, track.path)
            commit()
            self.assertEqual(db.Track.select().count(), 1)

        track = db.Track.select().first()
        new_path = os.path.abspath(os.path.join(os.path.dirname(track.path), '..', 'silence.mp3'))
        self.scanner.move_file(track.path, new_path)
        commit()
        self.assertEqual(db.Track.select().count(), 1)
        self.assertEqual(track.path, new_path)

    @db_session
    def test_rescan_corrupt_file(self):
        track = db.Track.select().first()
        self.scanner = Scanner(True)

        with self.__temporary_track_copy() as tf:
            self.scanner.scan(db.Folder[self.folderid])
            commit()
            self.assertEqual(db.Track.select().count(), 2)

            tf.seek(0, 0)
            tf.write(b'\x00' * 4096)
            tf.truncate()

            self.scanner.scan(db.Folder[self.folderid])
            commit()
            self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_rescan_removed_file(self):
        track = db.Track.select().first()

        with self.__temporary_track_copy() as tf:
            self.scanner.scan(db.Folder[self.folderid])
            commit()
            self.assertEqual(db.Track.select().count(), 2)

        self.scanner.scan(db.Folder[self.folderid])
        commit()
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_scan_tag_change(self):
        self.scanner = Scanner(True)
        folder = db.Folder[self.folderid]

        with self.__temporary_track_copy() as tf:
            self.scanner.scan(folder)
            commit()
            copy = db.Track.get(path = tf.name)
            self.assertEqual(copy.artist.name, 'Some artist')
            self.assertEqual(copy.album.name, 'Awesome album')

            tags = mutagen.File(copy.path, easy = True)
            tags['artist'] = 'Renamed artist'
            tags['album'] = 'Crappy album'
            tags.save()

            self.scanner.scan(folder)
            self.scanner.finish()
            self.assertEqual(copy.artist.name, 'Renamed artist')
            self.assertEqual(copy.album.name, 'Crappy album')
            self.assertIsNotNone(db.Artist.get(name = 'Some artist'))
            self.assertIsNotNone(db.Album.get(name = 'Awesome album'))

    def test_stats(self):
        self.assertEqual(self.scanner.stats(), ((1,1,1),(0,0,0)))

if __name__ == '__main__':
    unittest.main()


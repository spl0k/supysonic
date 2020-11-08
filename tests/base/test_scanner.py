#!/usr/bin/env python
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import io
import mutagen
import os
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
        db.init_database("sqlite:")

        with db_session:
            folder = FolderManager.add("folder", os.path.abspath("tests/assets/folder"))
            self.assertIsNotNone(folder)

        self.folderid = folder.id
        self.__scan()

    def tearDown(self):
        db.release_database()

    @contextmanager
    def __temporary_track_copy(self):
        track = db.Track.select().first()
        with tempfile.NamedTemporaryFile(
            dir=os.path.dirname(track.path), delete=False
        ) as tf:
            with io.open(track.path, "rb") as f:
                tf.write(f.read())
        try:
            yield tf.name
        finally:
            os.remove(tf.name)

    def __scan(self, force=False):
        self.scanner = Scanner(force=force)
        self.scanner.queue_folder("folder")
        self.scanner.run()
        commit()

    @db_session
    def test_scan(self):
        self.assertEqual(db.Track.select().count(), 1)

        self.assertRaises(TypeError, self.scanner.queue_folder, None)
        self.assertRaises(
            TypeError, self.scanner.queue_folder, db.Folder[self.folderid]
        )

    @db_session
    def test_rescan(self):
        self.__scan()
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_force_rescan(self):
        self.__scan(True)
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_scan_file(self):
        self.scanner.scan_file("/some/inexistent/path")
        commit()
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_remove_file(self):
        track = db.Track.select().first()
        self.assertRaises(TypeError, self.scanner.remove_file, None)
        self.assertRaises(TypeError, self.scanner.remove_file, track)

        self.scanner.remove_file("/some/inexistent/path")
        commit()
        self.assertEqual(db.Track.select().count(), 1)

        self.scanner.remove_file(track.path)
        self.scanner.prune()
        commit()
        self.assertEqual(db.Track.select().count(), 0)
        self.assertEqual(db.Album.select().count(), 0)
        self.assertEqual(db.Artist.select().count(), 0)

    @db_session
    def test_move_file(self):
        track = db.Track.select().first()
        self.assertRaises(TypeError, self.scanner.move_file, None, "string")
        self.assertRaises(TypeError, self.scanner.move_file, track, "string")
        self.assertRaises(TypeError, self.scanner.move_file, "string", None)
        self.assertRaises(TypeError, self.scanner.move_file, "string", track)

        self.scanner.move_file("/some/inexistent/path", track.path)
        commit()
        self.assertEqual(db.Track.select().count(), 1)

        self.scanner.move_file(track.path, track.path)
        commit()
        self.assertEqual(db.Track.select().count(), 1)

        self.assertRaises(
            Exception, self.scanner.move_file, track.path, "/some/inexistent/path"
        )

        with self.__temporary_track_copy() as tf:
            self.__scan()
            self.assertEqual(db.Track.select().count(), 2)
            self.scanner.move_file(tf, track.path)
            commit()
            self.assertEqual(db.Track.select().count(), 1)

        track = db.Track.select().first()
        new_path = track.path.replace("silence", "silence_moved")
        self.scanner.move_file(track.path, new_path)
        commit()
        self.assertEqual(db.Track.select().count(), 1)
        self.assertEqual(track.path, new_path)

    @db_session
    def test_rescan_corrupt_file(self):
        track = db.Track.select().first()

        with self.__temporary_track_copy() as tf:
            self.__scan()
            self.assertEqual(db.Track.select().count(), 2)

            with open(tf, "wb") as f:
                f.seek(0, 0)
                f.write(b"\x00" * 4096)
                f.truncate()

            self.__scan(True)
            self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_rescan_removed_file(self):
        track = db.Track.select().first()

        with self.__temporary_track_copy():
            self.__scan()
            self.assertEqual(db.Track.select().count(), 2)

        self.__scan()
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_scan_tag_change(self):
        folder = db.Folder[self.folderid]

        with self.__temporary_track_copy() as tf:
            self.__scan()
            copy = db.Track.get(path=tf)
            self.assertEqual(copy.artist.name, "Some artist")
            self.assertEqual(copy.album.name, "Awesome album")

            tags = mutagen.File(copy.path, easy=True)
            tags["artist"] = "Renamed artist"
            tags["album"] = "Crappy album"
            tags.save()

            self.__scan(True)
            self.assertEqual(copy.artist.name, "Renamed artist")
            self.assertEqual(copy.album.name, "Crappy album")
            self.assertIsNotNone(db.Artist.get(name="Some artist"))
            self.assertIsNotNone(db.Album.get(name="Awesome album"))

    def test_stats(self):
        stats = self.scanner.stats()
        self.assertEqual(stats.added.artists, 1)
        self.assertEqual(stats.added.albums, 1)
        self.assertEqual(stats.added.tracks, 1)
        self.assertEqual(stats.deleted.artists, 0)
        self.assertEqual(stats.deleted.albums, 0)
        self.assertEqual(stats.deleted.tracks, 0)


if __name__ == "__main__":
    unittest.main()

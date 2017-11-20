#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2017 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from supysonic import db
from supysonic.managers.folder import FolderManager

import os
import io
import shutil
import tempfile
import unittest
import uuid

class FolderManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory
        self.store = db.get_store("sqlite:")
        # Read schema from file
        with io.open('schema/sqlite.sql', 'r') as sql:
            schema = sql.read()
            # Create tables on memory database
            for command in schema.split(';'):
                self.store.execute(command)

        # Create some temporary directories
        self.media_dir = tempfile.mkdtemp()
        self.music_dir = tempfile.mkdtemp()
        # Add test folders
        self.assertEqual(FolderManager.add(self.store, 'media', self.media_dir), FolderManager.SUCCESS)
        self.assertEqual(FolderManager.add(self.store, 'music', self.music_dir), FolderManager.SUCCESS)

        folder = db.Folder()
        folder.root = False
        folder.name = 'non-root'
        folder.path = os.path.join(self.music_dir, 'subfolder')
        self.store.add(folder)

        artist = db.Artist()
        artist.name = 'Artist'

        album = db.Album()
        album.name = 'Album'
        album.artist = artist

        root = self.store.find(db.Folder, db.Folder.name == 'media').one()
        track = db.Track()
        track.title = 'Track'
        track.artist = artist
        track.album = album
        track.disc = 1
        track.number = 1
        track.path = os.path.join(self.media_dir, 'somefile')
        track.folder = root
        track.root_folder = root
        track.duration = 2
        track.content_type = 'audio/mpeg'
        track.bitrate = 320
        track.last_modification = 0
        self.store.add(track)

        self.store.commit()

    def tearDown(self):
        shutil.rmtree(self.media_dir)
        shutil.rmtree(self.music_dir)

    def test_get_folder(self):
        # Get existing folders
        for name in ['media', 'music']:
            folder = self.store.find(db.Folder, db.Folder.name == name, db.Folder.root == True).one()
            self.assertEqual(FolderManager.get(self.store, folder.id), (FolderManager.SUCCESS, folder))

        # Get with invalid UUID
        self.assertEqual(FolderManager.get(self.store, 'invalid-uuid'), (FolderManager.INVALID_ID, None))
        self.assertEqual(FolderManager.get(self.store, 0xdeadbeef), (FolderManager.INVALID_ID, None))

        # Non-existent folder
        self.assertEqual(FolderManager.get(self.store, uuid.uuid4()), (FolderManager.NO_SUCH_FOLDER, None))

    def test_add_folder(self):
        # Added in setUp()
        self.assertEqual(self.store.find(db.Folder).count(), 3)

        # Create duplicate
        self.assertEqual(FolderManager.add(self.store,'media', self.media_dir), FolderManager.NAME_EXISTS)
        self.assertEqual(self.store.find(db.Folder, db.Folder.name == 'media').count(), 1)

        # Duplicate path
        self.assertEqual(FolderManager.add(self.store,'new-folder', self.media_dir), FolderManager.PATH_EXISTS)
        self.assertEqual(self.store.find(db.Folder, db.Folder.path == self.media_dir).count(), 1)

        # Invalid path
        path = os.path.abspath('/this/not/is/valid')
        self.assertEqual(FolderManager.add(self.store,'invalid-path', path), FolderManager.INVALID_PATH)
        self.assertEqual(self.store.find(db.Folder, db.Folder.path == path).count(), 0)

        # Subfolder of already added path
        path = os.path.join(self.media_dir, 'subfolder')
        os.mkdir(path)
        self.assertEqual(FolderManager.add(self.store,'subfolder', path), FolderManager.PATH_EXISTS)
        self.assertEqual(self.store.find(db.Folder).count(), 3)

        # Parent folder of an already added path
        path = os.path.join(self.media_dir, '..')
        self.assertEqual(FolderManager.add(self.store, 'parent', path), FolderManager.SUBPATH_EXISTS)
        self.assertEqual(self.store.find(db.Folder).count(), 3)

    def test_delete_folder(self):
        # Delete existing folders
        for name in ['media', 'music']:
            folder = self.store.find(db.Folder, db.Folder.name == name, db.Folder.root == True).one()
            self.assertEqual(FolderManager.delete(self.store, folder.id), FolderManager.SUCCESS)
            self.assertIsNone(self.store.get(db.Folder, folder.id))

        # Delete invalid UUID
        self.assertEqual(FolderManager.delete(self.store, 'invalid-uuid'), FolderManager.INVALID_ID)
        self.assertEqual(self.store.find(db.Folder).count(), 1) # 'non-root' remaining

        # Delete non-existent folder
        self.assertEqual(FolderManager.delete(self.store, uuid.uuid4()), FolderManager.NO_SUCH_FOLDER)
        self.assertEqual(self.store.find(db.Folder).count(), 1) # 'non-root' remaining

        # Delete non-root folder
        folder = self.store.find(db.Folder, db.Folder.name == 'non-root').one()
        self.assertEqual(FolderManager.delete(self.store, folder.id), FolderManager.NO_SUCH_FOLDER)
        self.assertEqual(self.store.find(db.Folder).count(), 1) # 'non-root' remaining

    def test_delete_by_name(self):
        # Delete existing folders
        for name in ['media', 'music']:
            self.assertEqual(FolderManager.delete_by_name(self.store, name), FolderManager.SUCCESS)
            self.assertEqual(self.store.find(db.Folder, db.Folder.name == name).count(), 0)

        # Delete non-existent folder
        self.assertEqual(FolderManager.delete_by_name(self.store, 'null'), FolderManager.NO_SUCH_FOLDER)
        self.assertEqual(self.store.find(db.Folder).count(), 1) # 'non-root' remaining

    def test_human_readable_error(self):
        values = [ FolderManager.SUCCESS, FolderManager.INVALID_ID, FolderManager.NAME_EXISTS,
            FolderManager.INVALID_PATH, FolderManager.PATH_EXISTS, FolderManager.NO_SUCH_FOLDER,
            FolderManager.SUBPATH_EXISTS, 1594826, 'string', uuid.uuid4() ]
        for value in values:
            self.assertIsInstance(FolderManager.error_str(value), basestring)

if __name__ == '__main__':
    unittest.main()


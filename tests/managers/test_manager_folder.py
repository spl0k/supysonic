#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from supysonic import db
from supysonic.managers.folder import FolderManager
from supysonic.py23 import strtype

import os
import io
import shutil
import tempfile
import unittest
import uuid

from pony.orm import db_session, ObjectNotFound

class FolderManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory
        db.init_database('sqlite:', True)

        # Create some temporary directories
        self.media_dir = tempfile.mkdtemp()
        self.music_dir = tempfile.mkdtemp()

    def tearDown(self):
        db.release_database()
        shutil.rmtree(self.media_dir)
        shutil.rmtree(self.music_dir)

    @db_session
    def create_folders(self):
        # Add test folders
        self.assertEqual(FolderManager.add('media', self.media_dir), FolderManager.SUCCESS)
        self.assertEqual(FolderManager.add('music', self.music_dir), FolderManager.SUCCESS)

        folder = db.Folder(
            root = False,
            name = 'non-root',
            path = os.path.join(self.music_dir, 'subfolder')
        )

        artist = db.Artist(name = 'Artist')
        album = db.Album(name = 'Album', artist = artist)

        root = db.Folder.get(name = 'media')
        track = db.Track(
            title = 'Track',
            artist = artist,
            album = album,
            disc = 1,
            number = 1,
            path = os.path.join(self.media_dir, 'somefile'),
            folder = root,
            root_folder = root,
            duration = 2,
            content_type = 'audio/mpeg',
            bitrate = 320,
            last_modification = 0
        )

    @db_session
    def test_get_folder(self):
        self.create_folders()

        # Get existing folders
        for name in ['media', 'music']:
            folder = db.Folder.get(name = name, root = True)
            self.assertEqual(FolderManager.get(folder.id), (FolderManager.SUCCESS, folder))

        # Get with invalid UUID
        self.assertEqual(FolderManager.get('invalid-uuid'), (FolderManager.INVALID_ID, None))
        self.assertEqual(FolderManager.get(0xdeadbeef), (FolderManager.INVALID_ID, None))

        # Non-existent folder
        self.assertEqual(FolderManager.get(uuid.uuid4()), (FolderManager.NO_SUCH_FOLDER, None))

    @db_session
    def test_add_folder(self):
        self.create_folders()
        self.assertEqual(db.Folder.select().count(), 3)

        # Create duplicate
        self.assertEqual(FolderManager.add('media', self.media_dir), FolderManager.NAME_EXISTS)
        self.assertEqual(db.Folder.select(lambda f: f.name == 'media').count(), 1)

        # Duplicate path
        self.assertEqual(FolderManager.add('new-folder', self.media_dir), FolderManager.PATH_EXISTS)
        self.assertEqual(db.Folder.select(lambda f: f.path == self.media_dir).count(), 1)

        # Invalid path
        path = os.path.abspath('/this/not/is/valid')
        self.assertEqual(FolderManager.add('invalid-path', path), FolderManager.INVALID_PATH)
        self.assertFalse(db.Folder.exists(path = path))

        # Subfolder of already added path
        path = os.path.join(self.media_dir, 'subfolder')
        os.mkdir(path)
        self.assertEqual(FolderManager.add('subfolder', path), FolderManager.PATH_EXISTS)
        self.assertEqual(db.Folder.select().count(), 3)

        # Parent folder of an already added path
        path = os.path.join(self.media_dir, '..')
        self.assertEqual(FolderManager.add('parent', path), FolderManager.SUBPATH_EXISTS)
        self.assertEqual(db.Folder.select().count(), 3)

    @db_session
    def test_delete_folder(self):
        self.create_folders()

        # Delete existing folders
        for name in ['media', 'music']:
            folder = db.Folder.get(name = name, root = True)
            self.assertEqual(FolderManager.delete(folder.id), FolderManager.SUCCESS)
            self.assertRaises(ObjectNotFound, db.Folder.__getitem__, folder.id)

        # Delete invalid UUID
        self.assertEqual(FolderManager.delete('invalid-uuid'), FolderManager.INVALID_ID)
        self.assertEqual(db.Folder.select().count(), 1) # 'non-root' remaining

        # Delete non-existent folder
        self.assertEqual(FolderManager.delete(uuid.uuid4()), FolderManager.NO_SUCH_FOLDER)
        self.assertEqual(db.Folder.select().count(), 1) # 'non-root' remaining

        # Delete non-root folder
        folder = db.Folder.get(name = 'non-root')
        self.assertEqual(FolderManager.delete(folder.id), FolderManager.NO_SUCH_FOLDER)
        self.assertEqual(db.Folder.select().count(), 1) # 'non-root' remaining

    @db_session
    def test_delete_by_name(self):
        self.create_folders()

        # Delete existing folders
        for name in ['media', 'music']:
            self.assertEqual(FolderManager.delete_by_name(name), FolderManager.SUCCESS)
            self.assertFalse(db.Folder.exists(name = name))

        # Delete non-existent folder
        self.assertEqual(FolderManager.delete_by_name('null'), FolderManager.NO_SUCH_FOLDER)
        self.assertEqual(db.Folder.select().count(), 1) # 'non-root' remaining

    def test_human_readable_error(self):
        values = [ FolderManager.SUCCESS, FolderManager.INVALID_ID, FolderManager.NAME_EXISTS,
            FolderManager.INVALID_PATH, FolderManager.PATH_EXISTS, FolderManager.NO_SUCH_FOLDER,
            FolderManager.SUBPATH_EXISTS, 1594826, 'string', uuid.uuid4() ]
        for value in values:
            self.assertIsInstance(FolderManager.error_str(value), strtype)

if __name__ == '__main__':
    unittest.main()


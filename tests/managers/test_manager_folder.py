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
import shutil
import tempfile
import unittest
import uuid

class FolderManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory
        self.store = db.get_store("sqlite:")
        # Read schema from file
        with open('schema/sqlite.sql') as sql:
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
        # Non-existent folder
        self.assertEqual(FolderManager.get(self.store, uuid.uuid4()), (FolderManager.NO_SUCH_FOLDER, None))

    def test_add_folder(self):
        # Create duplicate
        self.assertEqual(FolderManager.add(self.store,'media', self.media_dir), FolderManager.NAME_EXISTS)
        # Duplicate path
        self.assertEqual(FolderManager.add(self.store,'new-folder', self.media_dir), FolderManager.PATH_EXISTS)
        # Invalid path
        self.assertEqual(FolderManager.add(self.store,'invalid-path', os.path.abspath('/this/not/is/valid')), FolderManager.INVALID_PATH)
        # Subfolder of already added path
        os.mkdir(os.path.join(self.media_dir, 'subfolder'))
        self.assertEqual(FolderManager.add(self.store,'subfolder', os.path.join(self.media_dir, 'subfolder')), FolderManager.PATH_EXISTS)

    def test_delete_folder(self):
        # Delete existing folders
        for name in ['media', 'music']:
            folder = self.store.find(db.Folder, db.Folder.name == name, db.Folder.root == True).one()
            self.assertEqual(FolderManager.delete(self.store, folder.id), FolderManager.SUCCESS)
        # Delete invalid UUID
        self.assertEqual(FolderManager.delete(self.store, 'invalid-uuid'), FolderManager.INVALID_ID)
        # Delete non-existent folder
        self.assertEqual(FolderManager.delete(self.store, uuid.uuid4()), FolderManager.NO_SUCH_FOLDER)
        # Delete non-root folder
        folder = self.store.find(db.Folder, db.Folder.name == 'non-root').one()
        self.assertEqual(FolderManager.delete(self.store, folder.id), FolderManager.NO_SUCH_FOLDER)

    def test_delete_by_name(self):
        # Delete existing folders
        for name in ['media', 'music']:
            self.assertEqual(FolderManager.delete_by_name(self.store, name), FolderManager.SUCCESS)
        # Delete non-existent folder
        self.assertEqual(FolderManager.delete_by_name(self.store, 'null'), FolderManager.NO_SUCH_FOLDER)

if __name__ == '__main__':
    unittest.main()

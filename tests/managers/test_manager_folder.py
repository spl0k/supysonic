#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2018 Alban 'spl0k' Féron
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

from pony.orm import db_session, ObjectNotFound


class FolderManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory
        db.init_database("sqlite:")

        # Create some temporary directories
        self.media_dir = tempfile.mkdtemp()
        self.music_dir = tempfile.mkdtemp()

    def tearDown(self):
        db.release_database()
        shutil.rmtree(self.media_dir)
        shutil.rmtree(self.music_dir)

    def create_folders(self):
        # Add test folders
        self.assertIsNotNone(FolderManager.add("media", self.media_dir))
        self.assertIsNotNone(FolderManager.add("music", self.music_dir))

        folder = db.Folder(
            root=False, name="non-root", path=os.path.join(self.music_dir, "subfolder")
        )

        artist = db.Artist(name="Artist")
        album = db.Album(name="Album", artist=artist)

        root = db.Folder.get(name="media")
        track = db.Track(
            title="Track",
            artist=artist,
            album=album,
            disc=1,
            number=1,
            path=os.path.join(self.media_dir, "somefile"),
            folder=root,
            root_folder=root,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

    @db_session
    def test_get_folder(self):
        self.create_folders()

        # Get existing folders
        for name in ["media", "music"]:
            folder = db.Folder.get(name=name, root=True)
            self.assertEqual(FolderManager.get(folder.id), folder)

        # Get with invalid UUID
        self.assertRaises(ValueError, FolderManager.get, "invalid-uuid")
        self.assertRaises(ValueError, FolderManager.get, 0xDEADBEEF)

        # Non-existent folder
        self.assertRaises(ObjectNotFound, FolderManager.get, 1234567890)

    @db_session
    def test_add_folder(self):
        self.create_folders()
        self.assertEqual(db.Folder.select().count(), 3)

        # Create duplicate
        self.assertRaises(ValueError, FolderManager.add, "media", self.media_dir)
        self.assertEqual(db.Folder.select(lambda f: f.name == "media").count(), 1)

        # Duplicate path
        self.assertRaises(ValueError, FolderManager.add, "new-folder", self.media_dir)
        self.assertEqual(
            db.Folder.select(lambda f: f.path == self.media_dir).count(), 1
        )

        # Invalid path
        path = os.path.abspath("/this/not/is/valid")
        self.assertRaises(ValueError, FolderManager.add, "invalid-path", path)
        self.assertFalse(db.Folder.exists(path=path))

        # Subfolder of already added path
        path = os.path.join(self.media_dir, "subfolder")
        os.mkdir(path)
        self.assertRaises(ValueError, FolderManager.add, "subfolder", path)
        self.assertEqual(db.Folder.select().count(), 3)

        # Parent folder of an already added path
        path = os.path.join(self.media_dir, "..")
        self.assertRaises(ValueError, FolderManager.add, "parent", path)
        self.assertEqual(db.Folder.select().count(), 3)

    def test_delete_folder(self):
        with db_session:
            self.create_folders()

        with db_session:
            # Delete invalid Folder ID
            self.assertRaises(ValueError, FolderManager.delete, "invalid-uuid")
            self.assertEqual(db.Folder.select().count(), 3)

            # Delete non-existent folder
            self.assertRaises(ObjectNotFound, FolderManager.delete, 1234567890)
            self.assertEqual(db.Folder.select().count(), 3)

            # Delete non-root folder
            folder = db.Folder.get(name="non-root")
            self.assertRaises(ObjectNotFound, FolderManager.delete, folder.id)
            self.assertEqual(db.Folder.select().count(), 3)

        with db_session:
            # Delete existing folders
            for name in ["media", "music"]:
                folder = db.Folder.get(name=name, root=True)
                FolderManager.delete(folder.id)
                self.assertRaises(ObjectNotFound, db.Folder.__getitem__, folder.id)

            # Even if we have only 2 root folders, non-root should never exist and be cleaned anyway
            self.assertEqual(db.Folder.select().count(), 0)

    def test_delete_by_name(self):
        with db_session:
            self.create_folders()

        with db_session:
            # Delete non-existent folder
            self.assertRaises(ObjectNotFound, FolderManager.delete_by_name, "null")
            self.assertEqual(db.Folder.select().count(), 3)

        with db_session:
            # Delete existing folders
            for name in ["media", "music"]:
                FolderManager.delete_by_name(name)
                self.assertFalse(db.Folder.exists(name=name))


if __name__ == "__main__":
    unittest.main()

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2023 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from supysonic.db import (
    Folder,
    Album,
    Artist,
    RatingFolder,
    RatingTrack,
    StarredAlbum,
    StarredArtist,
    StarredFolder,
    StarredTrack,
    Track,
    User,
    init_database,
    release_database,
)
from supysonic.managers.folder import FolderManager

import os
import shutil
import tempfile
import unittest


class FolderManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory
        init_database("sqlite:")

        # Create some temporary directories
        self.media_dir = tempfile.mkdtemp()
        self.music_dir = tempfile.mkdtemp()

    def tearDown(self):
        release_database()
        shutil.rmtree(self.media_dir)
        shutil.rmtree(self.music_dir)

    def create_folders(self):
        # Add test folders
        media = FolderManager.add("media", self.media_dir)
        music = FolderManager.add("music", self.music_dir)
        self.assertIsNotNone(media)
        self.assertIsNotNone(music)

        Folder.create(
            root=False,
            parent=music,
            name="non-root",
            path=os.path.join(self.music_dir, "subfolder"),
        )

        artist = Artist.create(name="Artist")
        album = Album.create(name="Album", artist=artist)

        Track.create(
            title="Track",
            artist=artist,
            album=album,
            disc=1,
            number=1,
            path=os.path.join(self.media_dir, "somefile"),
            folder=media,
            root_folder=media,
            duration=2,
            bitrate=320,
            last_modification=0,
        )

    def create_annotations(self):
        track = Track.select().first()
        user = User.create(name="user", password="secret", salt="ABC+", last_play=track)
        folder = Folder.get(name="media")

        RatingFolder.create(user=user, rated=folder, rating=3)
        RatingTrack.create(user=user, rated=track, rating=3)

        StarredFolder.create(user=user, starred=folder)
        StarredArtist.create(user=user, starred=track.artist_id)
        StarredAlbum.create(user=user, starred=track.album_id)
        StarredTrack.create(user=user, starred=track)

    def test_get_folder(self):
        self.create_folders()

        # Get existing folders
        for name in ["media", "music"]:
            folder = Folder.get(name=name, root=True)
            self.assertEqual(FolderManager.get(folder.id), folder)

        # Get with invalid id
        self.assertRaises(ValueError, FolderManager.get, "invalid-uuid")

        # Non-existent folder
        self.assertRaises(Folder.DoesNotExist, FolderManager.get, 1234567890)

    def test_add_folder(self):
        self.create_folders()
        self.assertEqual(Folder.select().count(), 3)

        # Create duplicate
        self.assertRaises(ValueError, FolderManager.add, "media", self.media_dir)
        self.assertEqual(Folder.select().where(Folder.name == "media").count(), 1)

        # Duplicate path
        self.assertRaises(ValueError, FolderManager.add, "new-folder", self.media_dir)
        self.assertEqual(
            Folder.select().where(Folder.path == self.media_dir).count(), 1
        )

        # Invalid path
        path = os.path.abspath("/this/not/is/valid")
        self.assertRaises(ValueError, FolderManager.add, "invalid-path", path)
        self.assertFalse(Folder.select().where(Folder.path == path).exists())

        # Subfolder of already added path
        path = os.path.join(self.media_dir, "subfolder")
        os.mkdir(path)
        self.assertRaises(ValueError, FolderManager.add, "subfolder", path)
        self.assertEqual(Folder.select().count(), 3)

        # Parent folder of an already added path
        path = os.path.join(self.media_dir, "..")
        self.assertRaises(ValueError, FolderManager.add, "parent", path)
        self.assertEqual(Folder.select().count(), 3)

    def test_delete_folder(self):
        self.create_folders()

        # Delete invalid Folder ID
        self.assertRaises(ValueError, FolderManager.delete, "invalid-uuid")
        self.assertEqual(Folder.select().count(), 3)

        # Delete non-existent folder
        self.assertRaises(Folder.DoesNotExist, FolderManager.delete, 1234567890)
        self.assertEqual(Folder.select().count(), 3)

        # Delete non-root folder
        folder = Folder.get(name="non-root")
        self.assertRaises(Folder.DoesNotExist, FolderManager.delete, folder.id)
        self.assertEqual(Folder.select().count(), 3)

        # Create some annotation to ensure foreign keys are properly handled
        self.create_annotations()

        # Delete existing folders
        for name in ["media", "music"]:
            folder = Folder.get(name=name, root=True)
            FolderManager.delete(folder.id)
            self.assertRaises(Folder.DoesNotExist, Folder.__getitem__, folder.id)

        # Even if we have only 2 root folders, non-root should never exist and be cleaned anyway
        self.assertEqual(Folder.select().count(), 0)

    def test_delete_by_name(self):
        self.create_folders()

        # Delete non-existent folder
        self.assertRaises(Folder.DoesNotExist, FolderManager.delete_by_name, "null")
        self.assertEqual(Folder.select().count(), 3)

        # Create some annotation to ensure foreign keys are properly handled
        self.create_annotations()

        # Delete existing folders
        for name in ["media", "music"]:
            FolderManager.delete_by_name(name)
            self.assertFalse(Folder.select().where(Folder.name == name).exists())


if __name__ == "__main__":
    unittest.main()

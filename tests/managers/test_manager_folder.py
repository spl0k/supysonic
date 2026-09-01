# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import shutil
import tempfile
import unittest

from supysonic.daemon.client import DaemonClient
from supysonic.db import (
    Album,
    Artist,
    Folder,
    Playlist,
    PlaylistTrack,
    RatingFolder,
    RatingTrack,
    StarredAlbum,
    StarredArtist,
    StarredFolder,
    StarredTrack,
    Track,
    User,
    init_database,
)
from supysonic.managers.folder import FolderManager

from ..testbase import get_test_db_uri, teardown_test_db


class FolderManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory (or the configured test DB)
        uri, self.__tmp = get_test_db_uri(memory=True)
        init_database(uri)

        # Create some temporary directories
        self.media_dir = tempfile.mkdtemp()
        self.music_dir = tempfile.mkdtemp()

        self._manager = FolderManager(DaemonClient())

    def tearDown(self):
        teardown_test_db(self.__tmp)
        shutil.rmtree(self.media_dir)
        shutil.rmtree(self.music_dir)

    def create_folders(self):
        # Add test folders
        media = self._manager.add("media", self.media_dir)
        music = self._manager.add("music", self.music_dir)
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
        user = User.create(name="user", password="secret#ABC+", last_play=track)
        folder = Folder.get(name="media")

        RatingFolder.create(user=user, rated=folder, rating=3)
        RatingTrack.create(user=user, rated=track, rating=3)

        StarredFolder.create(user=user, starred=folder)
        StarredArtist.create(user=user, starred=track.artist_id)
        StarredAlbum.create(user=user, starred=track.album_id)
        StarredTrack.create(user=user, starred=track)

        playlist = Playlist.create(user=user, name="Playlist")
        playlist.add(track)

    def test_get_folder(self):
        self.create_folders()

        # Get existing folders
        for name in ["media", "music"]:
            folder = Folder.get(name=name, root=True)
            self.assertEqual(self._manager.get(folder.id), folder)

        # Get with invalid id
        self.assertRaises(ValueError, self._manager.get, "invalid-uuid")

        # Non-existent folder
        self.assertRaises(Folder.DoesNotExist, self._manager.get, 1234567890)

    def test_add_folder(self):
        self.create_folders()
        self.assertEqual(Folder.select().count(), 3)

        # Create duplicate
        self.assertRaises(ValueError, self._manager.add, "media", self.media_dir)
        self.assertEqual(Folder.select().where(Folder.name == "media").count(), 1)

        # Duplicate path
        self.assertRaises(ValueError, self._manager.add, "new-folder", self.media_dir)
        self.assertEqual(
            Folder.select().where(Folder.path == self.media_dir).count(), 1
        )

        # Invalid path
        path = os.path.abspath("/this/not/is/valid")
        self.assertRaises(ValueError, self._manager.add, "invalid-path", path)
        self.assertFalse(Folder.select().where(Folder.path == path).exists())

        # Subfolder of already added path
        path = os.path.join(self.media_dir, "subfolder")
        os.mkdir(path)
        self.assertRaises(ValueError, self._manager.add, "subfolder", path)
        self.assertEqual(Folder.select().count(), 3)

        # Parent folder of an already added path
        path = os.path.join(self.media_dir, "..")
        self.assertRaises(ValueError, self._manager.add, "parent", path)
        self.assertEqual(Folder.select().count(), 3)

    def test_add_folder_sharing_a_prefix(self):
        # Sibling folders whose paths share a string prefix are unrelated, and
        # neither containment check should treat them as nested
        container = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, container)

        paths = {}
        for name in ("music", "music2", "musicX"):
            paths[name] = os.path.join(container, name)
            os.mkdir(paths[name])

        # "music" is a prefix of an already registered path: it neither contains
        # "music2" nor is contained by it
        self._manager.add("music2", paths["music2"])
        self._manager.add("music", paths["music"])
        # and the other way around
        self._manager.add("musicX", paths["musicX"])

        self.assertEqual(Folder.select().count(), 3)

    def test_delete_hierarchy_spares_prefix_siblings(self):
        root = self._manager.add("media", self.media_dir)
        artist = Artist.create(name="Artist")
        album = Album.create(name="Album", artist=artist)

        for name in ("ab", "abc"):
            path = os.path.join(self.media_dir, name)
            folder = Folder.create(root=False, parent=root, name=name, path=path)
            Track.create(
                title=name,
                artist=artist,
                album=album,
                disc=1,
                number=1,
                path=os.path.join(path, "track"),
                folder=folder,
                root_folder=root,
                duration=2,
                bitrate=320,
                last_modification=0,
            )

        Folder.get(name="ab").delete_hierarchy()

        # "abc" merely starts with "ab", it isn't part of its hierarchy
        self.assertFalse(Folder.select().where(Folder.name == "ab").exists())
        self.assertTrue(Folder.select().where(Folder.name == "abc").exists())
        self.assertEqual(Track.select().count(), 1)
        self.assertEqual(Track.select().first().title, "abc")

    def test_unreachable_daemon_is_traced(self):
        # The daemon is optional so its absence isn't an error, but it does leave
        # the folder unwatched, which should at least be traceable.
        with self.assertLogs("supysonic.managers.folder", level="DEBUG") as cm:
            folder = self._manager.add("media", self.media_dir)
        self.assertIn("won't be watched", "\n".join(cm.output))

        with self.assertLogs("supysonic.managers.folder", level="DEBUG") as cm:
            self._manager.delete(folder.id)
        self.assertIn("stays watched", "\n".join(cm.output))

    def test_delete_folder(self):
        self.create_folders()

        # Delete invalid Folder ID
        self.assertRaises(ValueError, self._manager.delete, "invalid-uuid")
        self.assertEqual(Folder.select().count(), 3)

        # Delete non-existent folder
        self.assertRaises(Folder.DoesNotExist, self._manager.delete, 1234567890)
        self.assertEqual(Folder.select().count(), 3)

        # Delete non-root folder
        folder = Folder.get(name="non-root")
        self.assertRaises(Folder.DoesNotExist, self._manager.delete, folder.id)
        self.assertEqual(Folder.select().count(), 3)

        # Create some annotation to ensure foreign keys are properly handled
        self.create_annotations()

        # Delete existing folders
        for name in ["media", "music"]:
            folder = Folder.get(name=name, root=True)
            self._manager.delete(folder.id)
            self.assertRaises(Folder.DoesNotExist, Folder.__getitem__, folder.id)

        # Even if we have only 2 root folders, non-root should never exist and be cleaned anyway
        self.assertEqual(Folder.select().count(), 0)

        # Playlists outlive the tracks they held, minus the entries
        self.assertEqual(PlaylistTrack.select().count(), 0)
        self.assertEqual(Playlist.select().count(), 1)

    def test_delete_by_name(self):
        self.create_folders()

        # Delete non-existent folder
        self.assertRaises(Folder.DoesNotExist, self._manager.delete_by_name, "null")
        self.assertEqual(Folder.select().count(), 3)

        # Create some annotation to ensure foreign keys are properly handled
        self.create_annotations()

        # Delete existing folders
        for name in ["media", "music"]:
            self._manager.delete_by_name(name)
            self.assertFalse(Folder.select().where(Folder.name == name).exists())


if __name__ == "__main__":
    unittest.main()

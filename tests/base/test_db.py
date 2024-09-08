# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import re
import unittest
import uuid

from collections import namedtuple
from peewee import IntegrityError

from supysonic import db

date_regex = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


class DbTestCase(unittest.TestCase):
    def setUp(self):
        db.init_database("sqlite:")

    def tearDown(self):
        db.release_database()

    def create_some_folders(self):
        root_folder = db.Folder.create(root=True, name="Root folder", path="tests")

        f1 = db.Folder.create(
            root=False,
            name="Child folder",
            path="tests/assets",
            cover_art="cover.jpg",
            parent=root_folder,
        )

        f2 = db.Folder.create(
            root=False,
            name="Child folder (No Art)",
            path="tests/formats",
            parent=root_folder,
        )

        return root_folder, f1, f2

    def create_some_tracks(self, artist=None, album=None):
        root, child, child_2 = self.create_some_folders()

        if not artist:
            artist = db.Artist.create(name="Test artist")

        if not album:
            album = db.Album.create(artist=artist, name="Test Album")

        track1 = db.Track.create(
            title="Track Title",
            album=album,
            artist=artist,
            disc=1,
            number=1,
            duration=3599,
            has_art=True,
            bitrate=320,
            path="tests/assets/formats/silence.ogg",
            last_modification=1234,
            root_folder=root,
            folder=child,
        )

        track2 = db.Track.create(
            title="One Awesome Song",
            album=album,
            artist=artist,
            disc=1,
            number=2,
            duration=3600,
            bitrate=96,
            path="tests/assets/23bytes",
            last_modification=1234,
            root_folder=root,
            folder=child,
        )

        return track1, track2

    def create_track_in(self, folder, root, artist=None, album=None, has_art=True):
        artist = artist or db.Artist.create(name="Snazzy Artist")
        album = album or db.Album.create(artist=artist, name="Rockin' Album")
        return db.Track.create(
            title="Nifty Number",
            album=album,
            artist=artist,
            disc=1,
            number=1,
            duration=5,
            has_art=has_art,
            bitrate=96,
            path="tests/assets/formats/silence.flac",
            last_modification=1234,
            root_folder=root,
            folder=folder,
        )

    def create_user(self, name="Test User"):
        return db.User.create(name=name, password="secret", salt="ABC+")

    def create_playlist(self):
        playlist = db.Playlist.create(user=self.create_user(), name="Playlist!")

        return playlist

    def test_ensure_sqlite_foreign_keys(self):
        root, _, _ = self.create_some_folders()
        self.assertRaises(IntegrityError, root.delete_instance)

    def test_folder_base(self):
        root_folder, child_folder, child_noart = self.create_some_folders()
        track_embededart = self.create_track_in(child_noart, root_folder)

        MockUser = namedtuple("User", ["id"])
        user = MockUser(uuid.uuid4())

        root = root_folder.as_subsonic_child(user)
        self.assertIsInstance(root, dict)
        self.assertIn("id", root)
        self.assertIn("isDir", root)
        self.assertIn("title", root)
        self.assertIn("album", root)
        self.assertIn("created", root)
        self.assertTrue(root["isDir"])
        self.assertEqual(root["title"], "Root folder")
        self.assertEqual(root["album"], "Root folder")
        self.assertRegex(root["created"], date_regex)

        child = child_folder.as_subsonic_child(user)
        self.assertIn("parent", child)
        self.assertIn("artist", child)
        self.assertIn("coverArt", child)
        self.assertEqual(child["parent"], str(root_folder.id))
        self.assertEqual(child["artist"], root_folder.name)
        self.assertEqual(child["coverArt"], child["id"])

        noart = child_noart.as_subsonic_child(user)
        self.assertIn("coverArt", noart)
        self.assertEqual(noart["coverArt"], str(track_embededart.id))

    def test_folder_annotation(self):
        root_folder, child_folder, _ = self.create_some_folders()

        user = self.create_user()
        db.StarredFolder.create(user=user, starred=root_folder)
        db.RatingFolder.create(user=user, rated=root_folder, rating=2)
        other = self.create_user("Other")
        db.RatingFolder.create(user=other, rated=root_folder, rating=5)

        root = root_folder.as_subsonic_child(user)
        self.assertIn("starred", root)
        self.assertIn("userRating", root)
        self.assertIn("averageRating", root)
        self.assertRegex(root["starred"], date_regex)
        self.assertEqual(root["userRating"], 2)
        self.assertEqual(root["averageRating"], 3.5)

        child = child_folder.as_subsonic_child(user)
        self.assertNotIn("starred", child)
        self.assertNotIn("userRating", child)

    def test_artist(self):
        artist = db.Artist.create(name="Test Artist")

        user = self.create_user()
        db.StarredArtist.create(user=user, starred=artist)

        artist_dict = artist.as_subsonic_artist(user)
        self.assertIsInstance(artist_dict, dict)
        self.assertIn("id", artist_dict)
        self.assertIn("name", artist_dict)
        self.assertIn("albumCount", artist_dict)
        self.assertIn("starred", artist_dict)
        self.assertEqual(artist_dict["name"], "Test Artist")
        self.assertEqual(artist_dict["albumCount"], 0)
        self.assertRegex(artist_dict["starred"], date_regex)

        db.Album.create(name="Test Artist", artist=artist)  # self-titled
        db.Album.create(name="The Album After The First One", artist=artist)

        artist_dict = artist.as_subsonic_artist(user)
        self.assertEqual(artist_dict["albumCount"], 2)

    def test_album(self):
        artist = db.Artist.create(name="Test Artist")
        album = db.Album.create(artist=artist, name="Test Album")

        user = self.create_user()
        db.StarredAlbum.create(user=user, starred=album)

        root_folder, folder_art, folder_noart = self.create_some_folders()
        track1 = self.create_track_in(
            folder_noart, root_folder, artist=artist, album=album
        )

        album_dict = album.as_subsonic_album(user)
        self.assertIsInstance(album_dict, dict)
        self.assertIn("id", album_dict)
        self.assertIn("name", album_dict)
        self.assertIn("artist", album_dict)
        self.assertIn("artistId", album_dict)
        self.assertIn("songCount", album_dict)
        self.assertIn("duration", album_dict)
        self.assertIn("created", album_dict)
        self.assertIn("starred", album_dict)
        self.assertIn("coverArt", album_dict)
        self.assertEqual(album_dict["name"], album.name)
        self.assertEqual(album_dict["artist"], artist.name)
        self.assertEqual(album_dict["artistId"], str(artist.id))
        self.assertEqual(album_dict["songCount"], 1)
        self.assertEqual(album_dict["duration"], 5)
        self.assertEqual(album_dict["coverArt"], str(track1.id))
        self.assertRegex(album_dict["created"], date_regex)
        self.assertRegex(album_dict["starred"], date_regex)

    def test_track(self):
        track1, track2 = self.create_some_tracks()

        assert track1.duration_str() == "59:59"
        assert track2.duration_str() == "01:00:00"

        # Assuming SQLite doesn't enforce foreign key constraints
        MockUser = namedtuple("User", ["id"])
        user = MockUser(uuid.uuid4())

        track1_dict = track1.as_subsonic_child(user, None)
        self.assertIsInstance(track1_dict, dict)
        self.assertIn("id", track1_dict)
        self.assertIn("parent", track1_dict)
        self.assertIn("isDir", track1_dict)
        self.assertIn("title", track1_dict)
        self.assertFalse(track1_dict["isDir"])
        self.assertIn("coverArt", track1_dict)
        self.assertEqual(track1_dict["coverArt"], track1_dict["id"])

        track2_dict = track2.as_subsonic_child(user, None)
        self.assertEqual(track2_dict["coverArt"], track2_dict["parent"])
        # ... we'll test the rest against the API XSD.

    def test_user(self):
        user = self.create_user()

        user_dict = user.as_subsonic_user()
        self.assertIsInstance(user_dict, dict)

    def test_chat(self):
        user = self.create_user()

        line = db.ChatMessage(user=user, message="Hello world!")

        line_dict = line.responsize()
        self.assertIsInstance(line_dict, dict)
        self.assertIn("username", line_dict)
        self.assertEqual(line_dict["username"], user.name)

    def test_playlist(self):
        playlist = self.create_playlist()
        playlist_dict = playlist.as_subsonic_playlist(playlist.user)
        self.assertIsInstance(playlist_dict, dict)

    def test_playlist_tracks(self):
        playlist = self.create_playlist()
        track1, track2 = self.create_some_tracks()

        playlist.add(track1)
        playlist.add(track2)
        self.assertSequenceEqual(playlist.get_tracks(), [track1, track2])

        playlist.add(track2.id)
        playlist.add(track1.id)
        self.assertSequenceEqual(
            playlist.get_tracks(), [track1, track2, track2, track1]
        )

        playlist.clear()
        self.assertSequenceEqual(playlist.get_tracks(), [])

        playlist.add(str(track1.id))
        self.assertSequenceEqual(playlist.get_tracks(), [track1])

        self.assertRaises(ValueError, playlist.add, "some string")
        self.assertRaises(NameError, playlist.add, 2345)

    def test_playlist_remove_tracks(self):
        playlist = self.create_playlist()
        track1, track2 = self.create_some_tracks()

        playlist.add(track1)
        playlist.add(track2)
        playlist.remove_at_indexes([0, 2])
        self.assertSequenceEqual(playlist.get_tracks(), [track2])

        playlist.add(track1)
        playlist.add(track2)
        playlist.add(track2)
        playlist.remove_at_indexes([2, 1])
        self.assertSequenceEqual(playlist.get_tracks(), [track2, track2])

        playlist.add(track1)
        playlist.remove_at_indexes([1, 1])
        self.assertSequenceEqual(playlist.get_tracks(), [track2, track1])

    def test_playlist_fixing(self):
        playlist = self.create_playlist()
        track1, track2 = self.create_some_tracks()

        playlist.add(track1)
        playlist.add(uuid.uuid4())
        playlist.add(track2)
        self.assertSequenceEqual(playlist.get_tracks(), [track1, track2])

        track2.delete_instance()
        self.assertSequenceEqual(playlist.get_tracks(), [track1])

        playlist.tracks = "{0},{0},some random garbage,{0}".format(track1.id)
        self.assertSequenceEqual(playlist.get_tracks(), [track1, track1, track1])


if __name__ == "__main__":
    unittest.main()

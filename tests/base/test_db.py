#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import io, re
from collections import namedtuple
import uuid

from supysonic import db

date_regex = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')

class DbTestCase(unittest.TestCase):
    def setUp(self):
        self.store = db.get_store(u'sqlite:')
        with io.open(u'schema/sqlite.sql', u'r') as f:
            for statement in f.read().split(u';'):
                self.store.execute(statement)

    def tearDown(self):
        self.store.close()

    def create_some_folders(self):
        root_folder = db.Folder()
        root_folder.root = True
        root_folder.name = u'Root folder'
        root_folder.path = u'tests'

        child_folder = db.Folder()
        child_folder.root = False
        child_folder.name = u'Child folder'
        child_folder.path = u'tests/assets'
        child_folder.has_cover_art = True
        child_folder.parent = root_folder

        self.store.add(root_folder)
        self.store.add(child_folder)
        self.store.commit()

        return root_folder, child_folder

    def create_some_tracks(self, artist = None, album = None):
        root, child = self.create_some_folders()

        if not artist:
            artist = db.Artist()
            artist.name = u'Test Artist'

        if not album:
            album = db.Album()
            album.artist = artist
            album.name = u'Test Album'

        track1 = db.Track()
        track1.title = u'Track Title'
        track1.album = album
        track1.artist = artist
        track1.disc = 1
        track1.number = 1
        track1.duration = 3
        track1.bitrate = 320
        track1.path = u'tests/assets/empty'
        track1.content_type = u'audio/mpeg'
        track1.last_modification = 1234
        track1.root_folder = root
        track1.folder = child
        self.store.add(track1)

        track2 = db.Track()
        track2.title = u'One Awesome Song'
        track2.album = album
        track2.artist = artist
        track2.disc = 1
        track2.number = 2
        track2.duration = 5
        track2.bitrate = 96
        track2.path = u'tests/assets/empty'
        track2.content_type = u'audio/mpeg'
        track2.last_modification = 1234
        track2.root_folder = root
        track2.folder = child
        self.store.add(track2)

        return track1, track2

    def create_playlist(self):
        user = db.User()
        user.name = u'Test User'
        user.password = u'secret'
        user.salt = u'ABC+'

        playlist = db.Playlist()
        playlist.user = user
        playlist.name = u'Playlist!'
        self.store.add(playlist)

        return playlist

    def test_folder_base(self):
        root_folder, child_folder = self.create_some_folders()

        MockUser = namedtuple(u'User', [ u'id' ])
        user = MockUser(uuid.uuid4())

        root = root_folder.as_subsonic_child(user)
        self.assertIsInstance(root, dict)
        self.assertIn(u'id', root)
        self.assertIn(u'isDir', root)
        self.assertIn(u'title', root)
        self.assertIn(u'album', root)
        self.assertIn(u'created', root)
        self.assertTrue(root[u'isDir'])
        self.assertEqual(root[u'title'], u'Root folder')
        self.assertEqual(root[u'album'], u'Root folder')
        self.assertRegexpMatches(root['created'], date_regex)

        child = child_folder.as_subsonic_child(user)
        self.assertIn(u'parent', child)
        self.assertIn(u'artist', child)
        self.assertIn(u'coverArt', child)
        self.assertEqual(child[u'parent'], str(root_folder.id))
        self.assertEqual(child[u'artist'], root_folder.name)
        self.assertEqual(child[u'coverArt'], child[u'id'])

    def test_folder_annotation(self):
        root_folder, child_folder = self.create_some_folders()

        # Assuming SQLite doesn't enforce foreign key constraints
        MockUser = namedtuple(u'User', [ u'id' ])
        user = MockUser(uuid.uuid4())

        star = db.StarredFolder()
        star.user_id = user.id
        star.starred_id = root_folder.id

        rating_user = db.RatingFolder()
        rating_user.user_id = user.id
        rating_user.rated_id = root_folder.id
        rating_user.rating = 2

        rating_other = db.RatingFolder()
        rating_other.user_id = uuid.uuid4()
        rating_other.rated_id = root_folder.id
        rating_other.rating = 5

        self.store.add(star)
        self.store.add(rating_user)
        self.store.add(rating_other)

        root = root_folder.as_subsonic_child(user)
        self.assertIn(u'starred', root)
        self.assertIn(u'userRating', root)
        self.assertIn(u'averageRating', root)
        self.assertRegexpMatches(root[u'starred'], date_regex)
        self.assertEqual(root[u'userRating'], 2)
        self.assertEqual(root[u'averageRating'], 3.5)

        child = child_folder.as_subsonic_child(user)
        self.assertNotIn(u'starred', child)
        self.assertNotIn(u'userRating', child)

    def test_artist(self):
        artist = db.Artist()
        artist.name = u'Test Artist'
        self.store.add(artist)

        # Assuming SQLite doesn't enforce foreign key constraints
        MockUser = namedtuple(u'User', [ u'id' ])
        user = MockUser(uuid.uuid4())

        star = db.StarredArtist()
        star.user_id = user.id
        star.starred_id = artist.id
        self.store.add(star)

        artist_dict = artist.as_subsonic_artist(user)
        self.assertIsInstance(artist_dict, dict)
        self.assertIn(u'id', artist_dict)
        self.assertIn(u'name', artist_dict)
        self.assertIn(u'albumCount', artist_dict)
        self.assertIn(u'starred', artist_dict)
        self.assertEqual(artist_dict[u'name'], u'Test Artist')
        self.assertEqual(artist_dict[u'albumCount'], 0)
        self.assertRegexpMatches(artist_dict[u'starred'], date_regex)

        album = db.Album()
        album.name = u'Test Artist' # self-titled
        artist.albums.add(album)

        album = db.Album()
        album.name = u'The Album After The Frist One'
        artist.albums.add(album)

        artist_dict = artist.as_subsonic_artist(user)
        self.assertEqual(artist_dict[u'albumCount'], 2)

    def test_album(self):
        artist = db.Artist()
        artist.name = u'Test Artist'

        album = db.Album()
        album.artist = artist
        album.name = u'Test Album'

        # Assuming SQLite doesn't enforce foreign key constraints
        MockUser = namedtuple(u'User', [ u'id' ])
        user = MockUser(uuid.uuid4())

        star = db.StarredAlbum()
        star.user_id = user.id
        star.starred = album

        self.store.add(album)
        self.store.add(star)

        # No tracks, shouldn't be stored under normal circumstances
        self.assertRaises(ValueError, album.as_subsonic_album, user)

        self.create_some_tracks(artist, album)

        album_dict = album.as_subsonic_album(user)
        self.assertIsInstance(album_dict, dict)
        self.assertIn(u'id', album_dict)
        self.assertIn(u'name', album_dict)
        self.assertIn(u'artist', album_dict)
        self.assertIn(u'artistId', album_dict)
        self.assertIn(u'songCount', album_dict)
        self.assertIn(u'duration', album_dict)
        self.assertIn(u'created', album_dict)
        self.assertIn(u'starred', album_dict)
        self.assertEqual(album_dict[u'name'], album.name)
        self.assertEqual(album_dict[u'artist'], artist.name)
        self.assertEqual(album_dict[u'artistId'], str(artist.id))
        self.assertEqual(album_dict[u'songCount'], 2)
        self.assertEqual(album_dict[u'duration'], 8)
        self.assertRegexpMatches(album_dict[u'created'], date_regex)
        self.assertRegexpMatches(album_dict[u'starred'], date_regex)

    def test_track(self):
        track1, track2 = self.create_some_tracks()

        # Assuming SQLite doesn't enforce foreign key constraints
        MockUser = namedtuple(u'User', [ u'id' ])
        user = MockUser(uuid.uuid4())

        track1_dict = track1.as_subsonic_child(user, None)
        self.assertIsInstance(track1_dict, dict)
        self.assertIn(u'id', track1_dict)
        self.assertIn(u'parent', track1_dict)
        self.assertIn(u'isDir', track1_dict)
        self.assertIn(u'title', track1_dict)
        self.assertFalse(track1_dict[u'isDir'])
        # ... we'll test the rest against the API XSD.

    def test_user(self):
        user = db.User()
        user.name = u'Test User'
        user.password = u'secret'
        user.salt = u'ABC+'

        user_dict = user.as_subsonic_user()
        self.assertIsInstance(user_dict, dict)

    def test_chat(self):
        user = db.User()
        user.name = u'Test User'
        user.password = u'secret'
        user.salt = u'ABC+'

        line = db.ChatMessage()
        line.user = user
        line.message = u'Hello world!'

        line_dict = line.responsize()
        self.assertIsInstance(line_dict, dict)
        self.assertIn(u'username', line_dict)
        self.assertEqual(line_dict[u'username'], user.name)

    def test_playlist(self):
        playlist = self.create_playlist()
        playlist_dict = playlist.as_subsonic_playlist(playlist.user)
        self.assertIsInstance(playlist_dict, dict)

    def test_playlist_tracks(self):
        playlist = self.create_playlist()
        track1, track2 = self.create_some_tracks()

        playlist.add(track1)
        playlist.add(track2)
        self.assertSequenceEqual(playlist.get_tracks(), [ track1, track2 ])

        playlist.add(track2.id)
        playlist.add(track1.id)
        self.assertSequenceEqual(playlist.get_tracks(), [ track1, track2, track2, track1 ])

        playlist.clear()
        self.assertSequenceEqual(playlist.get_tracks(), [])

        playlist.add(str(track1.id))
        self.assertSequenceEqual(playlist.get_tracks(), [ track1 ])

        self.assertRaises(ValueError, playlist.add, u'some string')
        self.assertRaises(NameError, playlist.add, 2345)

    def test_playlist_remove_tracks(self):
        playlist = self.create_playlist()
        track1, track2 = self.create_some_tracks()

        playlist.add(track1)
        playlist.add(track2)
        playlist.remove_at_indexes([ 0, 2 ])
        self.assertSequenceEqual(playlist.get_tracks(), [ track2 ])

        playlist.add(track1)
        playlist.add(track2)
        playlist.add(track2)
        playlist.remove_at_indexes([ 2, 1 ])
        self.assertSequenceEqual(playlist.get_tracks(), [ track2, track2 ])

        playlist.add(track1)
        playlist.remove_at_indexes([ 1, 1 ])
        self.assertSequenceEqual(playlist.get_tracks(), [ track2, track1 ])

    def test_playlist_fixing(self):
        playlist = self.create_playlist()
        track1, track2 = self.create_some_tracks()

        playlist.add(track1)
        playlist.add(uuid.uuid4())
        playlist.add(track2)
        self.assertSequenceEqual(playlist.get_tracks(), [ track1, track2 ])

        self.store.remove(track2)
        self.assertSequenceEqual(playlist.get_tracks(), [ track1 ])

        playlist.tracks = u'{0},{0},some random garbage,{0}'.format(track1.id)
        self.assertSequenceEqual(playlist.get_tracks(), [ track1, track1, track1 ])

if __name__ == '__main__':
    unittest.main()


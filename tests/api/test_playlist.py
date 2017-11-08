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

import uuid

from supysonic.db import Folder, Artist, Album, Track, Playlist, User

from .apitestbase import ApiTestBase

class PlaylistTestCase(ApiTestBase):
    def setUp(self):
        super(PlaylistTestCase, self).setUp()

        root = Folder()
        root.root = True
        root.name = 'Root folder'
        root.path = 'tests/assets'
        self.store.add(root)

        artist = Artist()
        artist.name = 'Artist'

        album = Album()
        album.name = 'Album'
        album.artist = artist

        songs = {}
        for num, song in enumerate([ 'One', 'Two', 'Three', 'Four' ]):
            track = Track()
            track.disc = 1
            track.number = num
            track.title = song
            track.duration = 2
            track.album = album
            track.artist = artist
            track.bitrate = 320
            track.path = 'tests/assets/empty'
            track.content_type = 'audio/mpeg'
            track.last_modification = 0
            track.root_folder = root
            track.folder = root

            self.store.add(track)
            songs[song] = track

        users = { u.name: u for u in self.store.find(User) }

        playlist = Playlist()
        playlist.user = users['alice']
        playlist.name = "Alice's"
        playlist.add(songs['One'])
        playlist.add(songs['Three'])
        self.store.add(playlist)

        playlist = Playlist()
        playlist.user = users['alice']
        playlist.public = True
        playlist.name = "Alice's public"
        playlist.add(songs['One'])
        playlist.add(songs['Two'])
        self.store.add(playlist)

        playlist = Playlist()
        playlist.user = users['bob']
        playlist.name = "Bob's"
        playlist.add(songs['Two'])
        playlist.add(songs['Four'])
        self.store.add(playlist)

        self.store.commit()

    def test_get_playlists(self):
        # get own playlists
        rv, child = self._make_request('getPlaylists', tag = 'playlists')
        self.assertEqual(len(child), 2)
        self.assertEqual(child[0].get('owner'), 'alice')
        self.assertEqual(child[1].get('owner'), 'alice')

        # get own and public
        rv, child = self._make_request('getPlaylists', { 'u': 'bob', 'p': 'B0b' }, tag = 'playlists')
        self.assertEqual(len(child), 2)
        self.assertTrue(child[0].get('owner') == 'alice' or child[1].get('owner') == 'alice')
        self.assertTrue(child[0].get('owner') == 'bob' or child[1].get('owner') == 'bob')
        self.assertIsNotNone(self._find(child, "./playlist[@owner='alice'][@public='true']"))

        # get other
        rv, child = self._make_request('getPlaylists', { 'username': 'bob' }, tag = 'playlists')
        self.assertEqual(len(child), 1)
        self.assertEqual(child[0].get('owner'), 'bob')

        # get other when not admin
        self._make_request('getPlaylists',  { 'u': 'bob', 'p': 'B0b', 'username': 'alice' }, error = 50)

        # get from unknown user
        self._make_request('getPlaylists', { 'username': 'johndoe' }, error = 70)

    def test_get_playlist(self):
        # missing param
        self._make_request('getPlaylist', error = 10)

        # invalid id
        self._make_request('getPlaylist', { 'id': 1234 }, error = 0)

        # unknown
        self._make_request('getPlaylist', { 'id': str(uuid.uuid4()) }, error = 70)

        # other's private from non admin
        playlist = self.store.find(Playlist, Playlist.public == False, Playlist.user_id == User.id, User.name == 'alice').one()
        self._make_request('getPlaylist', { 'u': 'bob', 'p': 'B0b', 'id': str(playlist.id) }, error = 50)

        # standard
        rv, child = self._make_request('getPlaylists', tag = 'playlists')
        rv, child = self._make_request('getPlaylist', { 'id': child[0].get('id') }, tag = 'playlist')
        self.assertEqual(child.get('songCount'), '2')
        self.assertEqual(self._xpath(child, 'count(./entry)'), 2) # don't count children, there may be 'allowedUser's (even though not supported by supysonic)
        self.assertEqual(child.get('duration'), '4')
        self.assertEqual(child[0].get('title'), 'One')
        self.assertTrue(child[1].get('title') == 'Two' or child[1].get('title') == 'Three') # depending on 'getPlaylists' result ordering

    def test_create_playlist(self):
        self._make_request('createPlaylist', error = 10)
        self._make_request('createPlaylist', { 'name': 'wrongId', 'songId': 'abc' }, error = 0)
        self._make_request('createPlaylist', { 'name': 'unknownId', 'songId': str(uuid.uuid4()) }, error = 70)
        self._make_request('createPlaylist', { 'playlistId': 'abc' }, error = 0)
        self._make_request('createPlaylist', { 'playlistId': str(uuid.uuid4()) }, error = 70)

        # create
        self._make_request('createPlaylist', { 'name': 'new playlist' }, skip_post = True)
        rv, child = self._make_request('getPlaylists', tag = 'playlists')
        self.assertEqual(len(child), 3)
        playlist = self._find(child, "./playlist[@name='new playlist']")
        self.assertEqual(len(playlist), 0)

        # "update" newly created
        self._make_request('createPlaylist', { 'playlistId': playlist.get('id') })
        rv, child = self._make_request('getPlaylists', tag = 'playlists')
        self.assertEqual(len(child), 3)

        # renaming
        self._make_request('createPlaylist', { 'playlistId': playlist.get('id'), 'name': 'renamed' })
        rv, child = self._make_request('getPlaylists', tag = 'playlists')
        self.assertEqual(len(child), 3)
        self.assertIsNone(self._find(child, "./playlist[@name='new playlist']"))
        playlist = self._find(child, "./playlist[@name='renamed']")
        self.assertIsNotNone(playlist)

        # update from other user
        self._make_request('createPlaylist', { 'u': 'bob', 'p': 'B0b', 'playlistId': playlist.get('id') }, error = 50)

        # create more useful playlist
        songs = { s.title: str(s.id) for s in self.store.find(Track) }
        self._make_request('createPlaylist', { 'name': 'songs', 'songId': map(lambda s: songs[s], [ 'Three', 'One', 'Two' ]) }, skip_post = True)
        playlist = self.store.find(Playlist, Playlist.name == 'songs').one()
        self.assertIsNotNone(playlist)
        rv, child = self._make_request('getPlaylist', { 'id': str(playlist.id) }, tag = 'playlist')
        self.assertEqual(child.get('songCount'), '3')
        self.assertEqual(self._xpath(child, 'count(./entry)'), 3)
        self.assertEqual(child[0].get('title'), 'Three')
        self.assertEqual(child[1].get('title'), 'One')
        self.assertEqual(child[2].get('title'), 'Two')

        # update
        self._make_request('createPlaylist', { 'playlistId': str(playlist.id), 'songId': songs['Two'] }, skip_post = True)
        rv, child = self._make_request('getPlaylist', { 'id': str(playlist.id) }, tag = 'playlist')
        self.assertEqual(child.get('songCount'), '1')
        self.assertEqual(self._xpath(child, 'count(./entry)'), 1)
        self.assertEqual(child[0].get('title'), 'Two')

    def test_delete_playlist(self):
        # check params
        self._make_request('deletePlaylist', error = 10)
        self._make_request('deletePlaylist', { 'id': 'string' }, error = 0)
        self._make_request('deletePlaylist', { 'id': str(uuid.uuid4()) }, error = 70)

        # delete unowned when not admin
        playlist = self.store.find(Playlist, Playlist.user_id == User.id, User.name == 'alice')[0]
        self._make_request('deletePlaylist', { 'u': 'bob', 'p': 'B0b', 'id': str(playlist.id) }, error = 50)
        self.assertEqual(self.store.find(Playlist).count(), 3)

        # delete owned
        self._make_request('deletePlaylist', { 'id': str(playlist.id) }, skip_post = True)
        self.assertEqual(self.store.find(Playlist).count(), 2)
        self._make_request('deletePlaylist', { 'id': str(playlist.id) }, error = 70)
        self.assertEqual(self.store.find(Playlist).count(), 2)

        # delete unowned when admin
        playlist = self.store.find(Playlist, Playlist.user_id == User.id, User.name == 'bob').one()
        self._make_request('deletePlaylist', { 'id': str(playlist.id) }, skip_post = True)
        self.assertEqual(self.store.find(Playlist).count(), 1)

    def test_update_playlist(self):
        self._make_request('updatePlaylist', error = 10)
        self._make_request('updatePlaylist', { 'playlistId': 1234 }, error = 0)
        self._make_request('updatePlaylist', { 'playlistId': str(uuid.uuid4()) }, error = 70)

        playlist = self.store.find(Playlist, Playlist.user_id == User.id, User.name == 'alice')[0]
        pid = str(playlist.id)
        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIdToAdd': 'string' }, error = 0)
        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIndexToRemove': 'string' }, error = 0)

        name = str(playlist.name)
        self._make_request('updatePlaylist', { 'u': 'bob', 'p': 'B0b', 'playlistId': pid, 'name': 'new name' }, error = 50)
        rv, child = self._make_request('getPlaylist', { 'id': pid }, tag = 'playlist')
        self.assertEqual(child.get('name'), name)
        self.assertEqual(self._xpath(child, 'count(./entry)'), 2)

        self._make_request('updatePlaylist', { 'playlistId': pid, 'name': 'new name' }, skip_post = True)
        rv, child = self._make_request('getPlaylist', { 'id': pid }, tag = 'playlist')
        self.assertEqual(child.get('name'), 'new name')
        self.assertEqual(self._xpath(child, 'count(./entry)'), 2)

        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIndexToRemove': [ -1, 2 ] }, skip_post = True)
        rv, child = self._make_request('getPlaylist', { 'id': pid }, tag = 'playlist')
        self.assertEqual(self._xpath(child, 'count(./entry)'), 2)

        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIndexToRemove': [ 0, 2 ] }, skip_post = True)
        rv, child = self._make_request('getPlaylist', { 'id': pid }, tag = 'playlist')
        self.assertEqual(self._xpath(child, 'count(./entry)'), 1)
        self.assertEqual(self._find(child, './entry').get('title'), 'Three')

        songs = { s.title: str(s.id) for s in self.store.find(Track) }

        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIdToAdd': [ songs['One'], songs['Two'], songs['Two'] ] }, skip_post = True)
        rv, child = self._make_request('getPlaylist', { 'id': pid }, tag = 'playlist')
        self.assertSequenceEqual(self._xpath(child, './entry/@title'), [ 'Three', 'One', 'Two', 'Two' ])

        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIndexToRemove': [ 2, 1 ] }, skip_post = True)
        rv, child = self._make_request('getPlaylist', { 'id': pid }, tag = 'playlist')
        self.assertSequenceEqual(self._xpath(child, './entry/@title'), [ 'Three', 'Two' ])

        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIdToAdd': songs['One'] }, skip_post = True)
        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIndexToRemove': [ 1, 1 ] }, skip_post = True)
        rv, child = self._make_request('getPlaylist', { 'id': pid }, tag = 'playlist')
        self.assertSequenceEqual(self._xpath(child, './entry/@title'), [ 'Three', 'One' ])

        self._make_request('updatePlaylist', { 'playlistId': pid, 'songIdToAdd': str(uuid.uuid4()) }, error = 70)
        rv, child = self._make_request('getPlaylist', { 'id': pid }, tag = 'playlist')
        self.assertEqual(self._xpath(child, 'count(./entry)'), 2)

if __name__ == '__main__':
    unittest.main()


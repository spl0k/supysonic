#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from supysonic.db import Folder, Artist, Album, Track, Playlist, User

from .frontendtestbase import FrontendTestBase

class PlaylistTestCase(FrontendTestBase):
    __module_to_test__ = 'supysonic.frontend'

    def setUp(self):
        super(PlaylistTestCase, self).setUp()

        folder = Folder()
        folder.name = 'Root'
        folder.path = 'tests/assets'
        folder.root = True

        artist = Artist()
        artist.name = 'Artist!'

        album = Album()
        album.name = 'Album!'
        album.artist = artist

        track = Track()
        track.path = 'tests/assets/23bytes'
        track.title = '23bytes'
        track.artist = artist
        track.album = album
        track.folder = folder
        track.root_folder = folder
        track.duration = 2
        track.disc = 1
        track.number = 1
        track.content_type = 'audio/mpeg'
        track.bitrate = 320
        track.last_modification = 0

        playlist = Playlist()
        playlist.name = 'Playlist!'
        playlist.user = self.store.find(User, User.name == 'alice').one()
        for _ in range(4):
            playlist.add(track)

        self.store.add(track)
        self.store.add(playlist)
        self.store.commit()

        self.playlist = playlist

    def test_index(self):
        self._login('alice', 'Alic3')
        rv = self.client.get('/playlist')
        self.assertIn('My playlists', rv.data)

    def test_details(self):
        self._login('alice', 'Alic3')
        rv = self.client.get('/playlist/string', follow_redirects = True)
        self.assertIn('Invalid', rv.data)
        rv = self.client.get('/playlist/' + str(uuid.uuid4()), follow_redirects = True)
        self.assertIn('Unknown', rv.data)
        rv = self.client.get('/playlist/' + str(self.playlist.id))
        self.assertIn('Playlist!', rv.data)
        self.assertIn('23bytes', rv.data)
        self.assertIn('Artist!', rv.data)
        self.assertIn('Album!', rv.data)

    def test_update(self):
        self._login('bob', 'B0b')
        rv = self.client.post('/playlist/string', follow_redirects = True)
        self.assertIn('Invalid', rv.data)
        rv = self.client.post('/playlist/' + str(uuid.uuid4()), follow_redirects = True)
        self.assertIn('Unknown', rv.data)
        rv = self.client.post('/playlist/' + str(self.playlist.id), follow_redirects = True)
        self.assertNotIn('updated', rv.data)
        self.assertIn('not allowed', rv.data)
        self._logout()

        self._login('alice', 'Alic3')
        rv = self.client.post('/playlist/' + str(self.playlist.id), follow_redirects = True)
        self.assertNotIn('updated', rv.data)
        self.assertIn('Missing', rv.data)
        self.assertEqual(self.playlist.name, 'Playlist!')

        rv = self.client.post('/playlist/' + str(self.playlist.id), data = { 'name': 'abc', 'public': True }, follow_redirects = True)
        self.assertIn('updated', rv.data)
        self.assertNotIn('not allowed', rv.data)
        self.assertEqual(self.playlist.name, 'abc')
        self.assertTrue(self.playlist.public)

    def test_delete(self):
        self._login('bob', 'B0b')
        rv = self.client.get('/playlist/del/string', follow_redirects = True)
        self.assertIn('Invalid', rv.data)
        rv = self.client.get('/playlist/del/' + str(uuid.uuid4()), follow_redirects = True)
        self.assertIn('Unknown', rv.data)
        rv = self.client.get('/playlist/del/' + str(self.playlist.id), follow_redirects = True)
        self.assertIn('not allowed', rv.data)
        self.assertEqual(self.store.find(Playlist).count(), 1)
        self._logout()

        self._login('alice', 'Alic3')
        rv = self.client.get('/playlist/del/' + str(self.playlist.id), follow_redirects = True)
        self.assertIn('deleted', rv.data)
        self.assertEqual(self.store.find(Playlist).count(), 0)

if __name__ == '__main__':
    unittest.main()


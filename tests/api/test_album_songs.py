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

from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase

class AlbumSongsTestCase(ApiTestBase):
    # I'm too lazy to write proper tests concerning the data on those endpoints
    # Let's just check paramter validation and ensure coverage

    def setUp(self):
        super(AlbumSongsTestCase, self).setUp()

        folder = Folder()
        folder.name = 'Root'
        folder.root = True
        folder.path = 'tests/assets'

        artist = Artist()
        artist.name = 'Artist'

        album = Album()
        album.name = 'Album'
        album.artist = artist

        track = Track()
        track.title = 'Track'
        track.album = album
        track.artist = artist
        track.disc = 1
        track.number = 1
        track.path = 'tests/assets/empty'
        track.folder = folder
        track.root_folder = folder
        track.duration = 2
        track.bitrate = 320
        track.content_type = 'audio/mpeg'
        track.last_modification = 0

        self.store.add(track)
        self.store.commit()

    def test_get_album_list(self):
        self._make_request('getAlbumList', error = 10)
        self._make_request('getAlbumList', { 'type': 'kraken' }, error = 0)
        self._make_request('getAlbumList', { 'type': 'random', 'size': 'huge' }, error = 0)
        self._make_request('getAlbumList', { 'type': 'newest', 'offset': 'minus one' }, error = 0)

        types = [ 'random', 'newest', 'highest', 'frequent', 'recent', 'alphabeticalByName',
            'alphabeticalByArtist', 'starred' ]
        for t in types:
            self._make_request('getAlbumList', { 'type': t }, tag = 'albumList', skip_post = True)

        rv, child = self._make_request('getAlbumList', { 'type': 'random' }, tag = 'albumList', skip_post = True)
        self.assertEqual(len(child), 10)
        rv, child = self._make_request('getAlbumList', { 'type': 'random', 'size': 3 }, tag = 'albumList', skip_post = True)
        self.assertEqual(len(child), 3)

        self.store.remove(self.store.find(Folder).one())
        rv, child = self._make_request('getAlbumList', { 'type': 'random' }, tag = 'albumList')
        self.assertEqual(len(child), 0)

    def test_get_album_list2(self):
        self._make_request('getAlbumList2', error = 10)
        self._make_request('getAlbumList2', { 'type': 'void' }, error = 0)
        self._make_request('getAlbumList2', { 'type': 'random', 'size': 'size_t' }, error = 0)
        self._make_request('getAlbumList2', { 'type': 'newest', 'offset': '&v + 2' }, error = 0)

        types = [ 'random', 'newest', 'frequent', 'recent', 'starred', 'alphabeticalByName', 'alphabeticalByArtist' ]
        for t in types:
            self._make_request('getAlbumList2', { 'type': t }, tag = 'albumList2', skip_post = True)

        rv, child = self._make_request('getAlbumList2', { 'type': 'random' }, tag = 'albumList2', skip_post = True)
        self.assertEqual(len(child), 10)
        rv, child = self._make_request('getAlbumList2', { 'type': 'random', 'size': 3 }, tag = 'albumList2', skip_post = True)
        self.assertEqual(len(child), 3)

        self.store.remove(self.store.find(Track).one())
        self.store.remove(self.store.find(Album).one())
        rv, child = self._make_request('getAlbumList2', { 'type': 'random' }, tag = 'albumList2')
        self.assertEqual(len(child), 0)

    def test_get_random_songs(self):
        self._make_request('getRandomSongs', { 'size': '8 floors' }, error = 0)
        self._make_request('getRandomSongs', { 'fromYear': 'year' }, error = 0)
        self._make_request('getRandomSongs', { 'toYear': 'year' }, error = 0)
        self._make_request('getRandomSongs', { 'musicFolderId': 'idid' }, error = 0)
        self._make_request('getRandomSongs', { 'musicFolderId': uuid.uuid4() }, error = 70)

        rv, child = self._make_request('getRandomSongs', tag = 'randomSongs')
        self.assertEqual(len(child), 10)
        rv, child = self._make_request('getRandomSongs', { 'size': 3 }, tag = 'randomSongs')
        self.assertEqual(len(child), 3)

        fid = self.store.find(Folder).one().id
        self._make_request('getRandomSongs', { 'fromYear': -52, 'toYear': '1984', 'genre': 'some cryptic subgenre youve never heard of', 'musicFolderId': fid }, tag = 'randomSongs')

    def test_now_playing(self):
        self._make_request('getNowPlaying', tag = 'nowPlaying')

    def test_get_starred(self):
        self._make_request('getStarred', tag = 'starred')

    def test_get_starred2(self):
        self._make_request('getStarred2', tag = 'starred2')

if __name__ == '__main__':
    unittest.main()


#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from pony.orm import db_session

from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase

class AlbumSongsTestCase(ApiTestBase):
    # I'm too lazy to write proper tests concerning the data on those endpoints
    # Let's just check paramter validation and ensure coverage

    def setUp(self):
        super(AlbumSongsTestCase, self).setUp()

        with db_session:
            folder = Folder(name = 'Root', root = True, path = 'tests/assets')
            artist = Artist(name = 'Artist')
            album = Album(name = 'Album', artist = artist)

            track = Track(
                title = 'Track',
                album = album,
                artist = artist,
                disc = 1,
                number = 1,
                path = 'tests/assets/empty',
                folder = folder,
                root_folder = folder,
                duration = 2,
                bitrate = 320,
                last_modification = 0
            )

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

        with db_session:
            Folder.get().delete()
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

        with db_session:
            Track.get().delete()
            Album.get().delete()
        rv, child = self._make_request('getAlbumList2', { 'type': 'random' }, tag = 'albumList2')
        self.assertEqual(len(child), 0)

    def test_get_random_songs(self):
        self._make_request('getRandomSongs', { 'size': '8 floors' }, error = 0)
        self._make_request('getRandomSongs', { 'fromYear': 'year' }, error = 0)
        self._make_request('getRandomSongs', { 'toYear': 'year' }, error = 0)
        self._make_request('getRandomSongs', { 'musicFolderId': 'idid' }, error = 0)
        self._make_request('getRandomSongs', { 'musicFolderId': uuid.uuid4() }, error = 70)

        rv, child = self._make_request('getRandomSongs', tag = 'randomSongs', skip_post = True)

        with db_session:
            fid = Folder.get().id
        self._make_request('getRandomSongs', { 'fromYear': -52, 'toYear': '1984', 'genre': 'some cryptic subgenre youve never heard of', 'musicFolderId': fid }, tag = 'randomSongs')

    def test_now_playing(self):
        self._make_request('getNowPlaying', tag = 'nowPlaying')

    def test_get_starred(self):
        self._make_request('getStarred', tag = 'starred')

    def test_get_starred2(self):
        self._make_request('getStarred2', tag = 'starred2')

if __name__ == '__main__':
    unittest.main()


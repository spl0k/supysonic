#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import requests
import uuid

from io import BytesIO
from PIL import Image
from pony.orm import db_session

from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase

class MediaTestCase(ApiTestBase):
    def setUp(self):
        super(MediaTestCase, self).setUp()

        with db_session:
            folder = Folder(
                name = 'Root',
                path = os.path.abspath('tests/assets'),
                root = True,
                cover_art = 'cover.jpg'
            )
            self.folderid = folder.id

            artist = Artist(name = 'Artist')
            album = Album(artist = artist, name = 'Album')

            track = Track(
                title = '23bytes',
                number = 1,
                disc = 1,
                artist = artist,
                album = album,
                path = os.path.abspath('tests/assets/23bytes'),
                root_folder = folder,
                folder = folder,
                duration = 2,
                bitrate = 320,
                content_type = 'audio/mpeg',
                last_modification = 0
            )
            self.trackid = track.id

            self.formats = [('mp3','mpeg'), ('flac','flac'), ('ogg','ogg')]
            for i in range(len(self.formats)):
                track_embeded_art = Track(
                    title = '[silence]',
                    number = 1,
                    disc = 1,
                    artist = artist,
                    album = album,
                    path = os.path.abspath('tests/assets/formats/silence.{0}'.format(self.formats[i][0])),
                    root_folder = folder,
                    folder = folder,
                    duration = 2,
                    bitrate = 320,
                    content_type = 'audio/{0}'.format(self.formats[i][1]),
                    last_modification = 0
                )
                self.formats[i] = track_embeded_art.id

    def test_stream(self):
        self._make_request('stream', error = 10)
        self._make_request('stream', { 'id': 'string' }, error = 0)
        self._make_request('stream', { 'id': str(uuid.uuid4()) }, error = 70)
        self._make_request('stream', { 'id': str(self.folderid) }, error = 70)
        self._make_request('stream', { 'id': str(self.trackid), 'maxBitRate': 'string' }, error = 0)
        self._make_request('stream', { 'id': str(self.trackid), 'timeOffset': 2 }, error = 0)
        self._make_request('stream', { 'id': str(self.trackid), 'size': '640x480' }, error = 0)

        rv = self.client.get('/rest/stream.view', query_string = { 'u': 'alice', 'p': 'Alic3', 'c': 'tests', 'id': str(self.trackid) })
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'audio/mpeg')
        self.assertEqual(len(rv.data), 23)
        with db_session:
            self.assertEqual(Track[self.trackid].play_count, 1)

    def test_download(self):
        self._make_request('download', error = 10)
        self._make_request('download', { 'id': 'string' }, error = 0)
        self._make_request('download', { 'id': str(uuid.uuid4()) }, error = 70)

        # download single file
        rv = self.client.get('/rest/download.view', query_string = { 'u': 'alice', 'p': 'Alic3', 'c': 'tests', 'id': str(self.trackid) })
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'audio/mpeg')
        self.assertEqual(len(rv.data), 23)
        with db_session:
            self.assertEqual(Track[self.trackid].play_count, 0)

        # dowload folder
        rv = self.client.get('/rest/download.view', query_string = { 'u': 'alice', 'p': 'Alic3', 'c': 'tests', 'id': str(self.folderid) })
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'application/zip')

    def test_get_cover_art(self):
        self._make_request('getCoverArt', error = 10)
        self._make_request('getCoverArt', { 'id': 'string' }, error = 0)
        self._make_request('getCoverArt', { 'id': str(uuid.uuid4()) }, error = 70)
        self._make_request('getCoverArt', { 'id': str(self.trackid) }, error = 70)
        self._make_request('getCoverArt', { 'id': str(self.folderid), 'size': 'large' }, error = 0)

        args = { 'u': 'alice', 'p': 'Alic3', 'c': 'tests', 'id': str(self.folderid) }
        rv = self.client.get('/rest/getCoverArt.view', query_string = args)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        im = Image.open(BytesIO(rv.data))
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(im.size, (420, 420))

        args['size'] = 600
        rv = self.client.get('/rest/getCoverArt.view', query_string = args)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        im = Image.open(BytesIO(rv.data))
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(im.size, (420, 420))

        args['size'] = 120
        rv = self.client.get('/rest/getCoverArt.view', query_string = args)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        im = Image.open(BytesIO(rv.data))
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(im.size, (120, 120))

        # rerequest, just in case
        rv = self.client.get('/rest/getCoverArt.view', query_string = args)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        im = Image.open(BytesIO(rv.data))
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(im.size, (120, 120))

        # TODO test non square covers

        # Test extracting cover art from embeded media
        for args['id'] in self.formats:
            rv = self.client.get('/rest/getCoverArt.view', query_string = args)
            self.assertEqual(rv.status_code, 200)
            self.assertEqual(rv.mimetype, 'image/png')
            im = Image.open(BytesIO(rv.data))
            self.assertEqual(im.format, 'PNG')
            self.assertEqual(im.size, (120, 120))

    def test_get_lyrics(self):
        self._make_request('getLyrics', error = 10)
        self._make_request('getLyrics', { 'artist': 'artist' }, error = 10)
        self._make_request('getLyrics', { 'title': 'title' }, error = 10)

        # Potentially skip the tests if ChartLyrics is down (which happens quite often)
        try:
            requests.get('http://api.chartlyrics.com/', timeout = 5)
        except requests.exceptions.Timeout:
            self.skipTest('ChartLyrics down')

        rv, child = self._make_request('getLyrics', { 'artist': 'some really long name hoping', 'title': 'to get absolutely no result' }, tag = 'lyrics')
        self.assertIsNone(child.text)

        # ChartLyrics
        rv, child = self._make_request('getLyrics', { 'artist': 'The Clash', 'title': 'London Calling' }, tag = 'lyrics')
        self.assertIn('live by the river', child.text)

        # Local file
        rv, child = self._make_request('getLyrics', { 'artist': 'artist', 'title': '23bytes' }, tag = 'lyrics')
        self.assertIn('null', child.text)

    def test_get_avatar(self):
        self._make_request('getAvatar', error = 0)

if __name__ == '__main__':
    unittest.main()


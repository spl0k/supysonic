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

import os.path
import uuid
from io import BytesIO
from PIL import Image

from supysonic.db import Folder, Artist, Album, Track

from .apitestbase import ApiTestBase

class MediaTestCase(ApiTestBase):
    def setUp(self):
        super(MediaTestCase, self).setUp()

        self.folder = Folder()
        self.folder.name = 'Root'
        self.folder.path = os.path.abspath('tests/assets')
        self.folder.root = True
        self.folder.has_cover_art = True # 420x420 PNG

        artist = Artist()
        artist.name = 'Artist'

        album = Album()
        album.artist = artist
        album.name = 'Album'

        self.track = Track()
        self.track.title = '23bytes'
        self.track.number = 1
        self.track.disc = 1
        self.track.artist = artist
        self.track.album = album
        self.track.path = os.path.abspath('tests/assets/23bytes')
        self.track.root_folder = self.folder
        self.track.folder = self.folder
        self.track.duration = 2
        self.track.bitrate = 320
        self.track.content_type = 'audio/mpeg'
        self.track.last_modification = 0

        self.store.add(self.track)
        self.store.commit()

    def test_stream(self):
        self._make_request('stream', error = 10)
        self._make_request('stream', { 'id': 'string' }, error = 0)
        self._make_request('stream', { 'id': str(uuid.uuid4()) }, error = 70)
        self._make_request('stream', { 'id': str(self.folder.id) }, error = 70)
        self._make_request('stream', { 'id': str(self.track.id), 'maxBitRate': 'string' }, error = 0)

        rv = self.client.get('/rest/stream.view', query_string = { 'u': 'alice', 'p': 'Alic3', 'c': 'tests', 'id': str(self.track.id) })
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'audio/mpeg')
        self.assertEqual(len(rv.data), 23)
        self.assertEqual(self.track.play_count, 1)

        # TODO test transcoding

    def test_download(self):
        self._make_request('download', error = 10)
        self._make_request('download', { 'id': 'string' }, error = 0)
        self._make_request('download', { 'id': str(uuid.uuid4()) }, error = 70)
        self._make_request('download', { 'id': str(self.folder.id) }, error = 70)

        rv = self.client.get('/rest/download.view', query_string = { 'u': 'alice', 'p': 'Alic3', 'c': 'tests', 'id': str(self.track.id) })
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'audio/mpeg')
        self.assertEqual(len(rv.data), 23)
        self.assertEqual(self.track.play_count, 0)

    def test_get_cover_art(self):
        self._make_request('getCoverArt', error = 10)
        self._make_request('getCoverArt', { 'id': 'string' }, error = 0)
        self._make_request('getCoverArt', { 'id': str(uuid.uuid4()) }, error = 70)
        self._make_request('getCoverArt', { 'id': str(self.track.id) }, error = 70)
        self._make_request('getCoverArt', { 'id': str(self.folder.id), 'size': 'large' }, error = 0)

        args = { 'u': 'alice', 'p': 'Alic3', 'c': 'tests', 'id': str(self.folder.id) }
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

        self.skipTest("config dependant test, config isn't test proof")
        args['size'] = 120
        rv = self.client.get('/rest/getCoverArt.view', query_string = args)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, 'image/jpeg')
        im = Image.open(BytesIO(rv.data))
        self.assertEqual(im.format, 'JPEG')
        self.assertEqual(im.size, (120, 120))

        # TODO test non square covers

    def test_get_lyrics(self):
        self._make_request('getLyrics', error = 10)
        self._make_request('getLyrics', { 'artist': 'artist' }, error = 10)
        self._make_request('getLyrics', { 'title': 'title' }, error = 10)

        rv, child = self._make_request('getLyrics', { 'artist': 'some really long name hoping', 'title': 'to get absolutely no result' }, tag = 'lyrics')
        self.assertIsNone(child.text)

        # ChartLyrics
        rv, child = self._make_request('getLyrics', { 'artist': 'The Clash', 'title': 'London Calling' }, tag = 'lyrics')
        self.assertIn('live by the river', child.text)

        self.skipTest('That weird logger/atexit error again')
        # Local file
        rv, child = self._make_request('getLyrics', { 'artist': 'artist', 'title': '23bytes' }, tag = 'lyrics')
        self.assertIn('null', child.text)
        print child

    def test_get_avatar(self):
        self._make_request('getAvatar', error = 0)

if __name__ == '__main__':
    unittest.main()


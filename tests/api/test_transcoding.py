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

from pony.orm import db_session

from supysonic.db import Folder, Track
from supysonic.managers.folder import FolderManager
from supysonic.scanner import Scanner

from .apitestbase import ApiTestBase

class TranscodingTestCase(ApiTestBase):
    def setUp(self):
        self.skipTest('Logging/atexit error')

        super(TranscodingTestCase, self).setUp()
        self._patch_client()

        FolderManager.add('Folder', 'tests/assets/folder')
        scanner = Scanner()
        with db_session:
            scanner.scan(Folder.get())
            scanner.finish()

            self.trackid = Track.get().id

    def _stream(self, **kwargs):
        kwargs.update({ 'u': 'alice', 'p': 'Alic3', 'c': 'tests', 'v': '1.8.0', 'id': self.trackid })

        rv = self.client.get('/rest/stream.view', query_string = kwargs)
        self.assertEqual(rv.status_code, 200)
        self.assertFalse(rv.mimetype.startswith('text/'))

        return rv

    def test_no_transcoding_available(self):
        self._make_request('stream', { 'id': self.trackid, 'format': 'wat' }, error = 0)

    def test_direct_transcode(self):
        rv = self._stream(maxBitRate = 96)
        self.assertIn('tests/assets/folder/silence.mp3', rv.data)
        self.assertTrue(rv.data.endswith('96'))

    def test_decode_encode(self):
        rv = self._stream(format = 'cat')
        self.assertEqual(rv.data, 'Pushing out some mp3 data...')

        rv = self._stream(format = 'md5')
        self.assertTrue(rv.data.startswith('dbb16c0847e5d8c3b1867604828cb50b'))

if __name__ == '__main__':
    unittest.main()


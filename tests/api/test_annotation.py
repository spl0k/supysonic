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

from supysonic.db import Folder, Artist, Album, Track, User, ClientPrefs

from .apitestbase import ApiTestBase

class AnnotationTestCase(ApiTestBase):
    def setUp(self):
        super(AnnotationTestCase, self).setUp()

        root = Folder()
        root.name = 'Root'
        root.root = True
        root.path = 'tests/assets'

        folder = Folder()
        folder.name = 'Folder'
        folder.path = 'tests/assets'
        folder.parent = root

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
        track.root_folder = root
        track.duration = 2
        track.bitrate = 320
        track.content_type = 'audio/mpeg'
        track.last_modification = 0

        self.store.add(track)
        self.store.commit()

        self.folder = folder
        self.artist = artist
        self.album = album
        self.track = track
        self.user = self.store.find(User, User.name == 'alice').one()

    def test_star(self):
        self._make_request('star', error = 10)
        self._make_request('star', { 'id': 'unknown' }, error = 0, skip_xsd = True)
        self._make_request('star', { 'albumId': 'unknown' }, error = 0)
        self._make_request('star', { 'artistId': 'unknown' }, error = 0)
        self._make_request('star', { 'id': str(uuid.uuid4()) }, error = 70, skip_xsd = True)
        self._make_request('star', { 'albumId': str(uuid.uuid4()) }, error = 70)
        self._make_request('star', { 'artistId': str(uuid.uuid4()) }, error = 70)

        self._make_request('star', { 'id': str(self.artist.id) }, error = 70, skip_xsd = True)
        self._make_request('star', { 'id': str(self.album.id) }, error = 70, skip_xsd = True)
        self._make_request('star', { 'id': str(self.track.id) }, skip_post = True)
        self.assertIn('starred', self.track.as_subsonic_child(self.user, ClientPrefs()))
        self._make_request('star', { 'id': str(self.track.id) }, error = 0, skip_xsd = True)

        self._make_request('star', { 'id': str(self.folder.id) }, skip_post = True)
        self.assertIn('starred', self.folder.as_subsonic_child(self.user))
        self._make_request('star', { 'id': str(self.folder.id) }, error = 0, skip_xsd = True)

        self._make_request('star', { 'albumId': str(self.folder.id) }, error = 70)
        self._make_request('star', { 'albumId': str(self.artist.id) }, error = 70)
        self._make_request('star', { 'albumId': str(self.track.id) }, error = 70)
        self._make_request('star', { 'albumId': str(self.album.id) }, skip_post = True)
        self.assertIn('starred', self.album.as_subsonic_album(self.user))
        self._make_request('star', { 'albumId': str(self.album.id) }, error = 0)

        self._make_request('star', { 'artistId': str(self.folder.id) }, error = 70)
        self._make_request('star', { 'artistId': str(self.album.id) }, error = 70)
        self._make_request('star', { 'artistId': str(self.track.id) }, error = 70)
        self._make_request('star', { 'artistId': str(self.artist.id) }, skip_post = True)
        self.assertIn('starred', self.artist.as_subsonic_artist(self.user))
        self._make_request('star', { 'artistId': str(self.artist.id) }, error = 0)

    def test_unstar(self):
        self._make_request('star', { 'id': [ str(self.folder.id), str(self.track.id) ], 'artistId': str(self.artist.id), 'albumId': str(self.album.id) }, skip_post = True)

        self._make_request('unstar', error = 10)
        self._make_request('unstar', { 'id': 'unknown' }, error = 0, skip_xsd = True)
        self._make_request('unstar', { 'albumId': 'unknown' }, error = 0)
        self._make_request('unstar', { 'artistId': 'unknown' }, error = 0)

        self._make_request('unstar', { 'id': str(self.track.id) }, skip_post = True)
        self.assertNotIn('starred', self.track.as_subsonic_child(self.user, ClientPrefs()))

        self._make_request('unstar', { 'id': str(self.folder.id) }, skip_post = True)
        self.assertNotIn('starred', self.folder.as_subsonic_child(self.user))

        self._make_request('unstar', { 'albumId': str(self.album.id) }, skip_post = True)
        self.assertNotIn('starred', self.album.as_subsonic_album(self.user))

        self._make_request('unstar', { 'artistId': str(self.artist.id) }, skip_post = True)
        self.assertNotIn('starred', self.artist.as_subsonic_artist(self.user))

    def test_set_rating(self):
        self._make_request('setRating', error = 10)
        self._make_request('setRating', { 'id': str(self.track.id) }, error = 10)
        self._make_request('setRating', { 'rating': 3 }, error = 10)
        self._make_request('setRating', { 'id': 'string', 'rating': 3 }, error = 0)
        self._make_request('setRating', { 'id': str(uuid.uuid4()), 'rating': 3 }, error = 70)
        self._make_request('setRating', { 'id': str(self.artist.id), 'rating': 3 }, error = 70)
        self._make_request('setRating', { 'id': str(self.album.id), 'rating': 3 }, error = 70)
        self._make_request('setRating', { 'id': str(self.track.id), 'rating': 'string' }, error = 0)
        self._make_request('setRating', { 'id': str(self.track.id), 'rating': -1 }, error = 0)
        self._make_request('setRating', { 'id': str(self.track.id), 'rating': 6 }, error = 0)

        prefs = ClientPrefs()
        self.assertNotIn('userRating', self.track.as_subsonic_child(self.user, prefs))

        for i in range(1, 6):
            self._make_request('setRating', { 'id': str(self.track.id), 'rating': i }, skip_post = True)
            self.assertEqual(self.track.as_subsonic_child(self.user, prefs)['userRating'], i)
        self._make_request('setRating', { 'id': str(self.track.id), 'rating': 0 }, skip_post = True)
        self.assertNotIn('userRating', self.track.as_subsonic_child(self.user, prefs))

        self.assertNotIn('userRating', self.folder.as_subsonic_child(self.user))
        for i in range(1, 6):
            self._make_request('setRating', { 'id': str(self.folder.id), 'rating': i }, skip_post = True)
            self.assertEqual(self.folder.as_subsonic_child(self.user)['userRating'], i)
        self._make_request('setRating', { 'id': str(self.folder.id), 'rating': 0 }, skip_post = True)
        self.assertNotIn('userRating', self.folder.as_subsonic_child(self.user))

    def test_scrobble(self):
        self._make_request('scrobble', error = 10)
        self._make_request('scrobble', { 'id': 'song' }, error = 0)
        self._make_request('scrobble', { 'id': str(uuid.uuid4()) }, error = 70)
        self._make_request('scrobble', { 'id': str(self.folder.id) }, error = 70)

        self.skipTest('Weird request context/logger issue at exit')
        self._make_request('scrobble', { 'id': str(self.track.id) })
        self._make_request('scrobble', { 'id': str(self.track.id), 'submission': True })
        self._make_request('scrobble', { 'id': str(self.track.id), 'submission': False })

if __name__ == '__main__':
    unittest.main()


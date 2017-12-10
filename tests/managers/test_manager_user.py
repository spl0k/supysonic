#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2017 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from supysonic import db
from supysonic.managers.user import UserManager

import unittest
import uuid
import io

class UserManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory
        self.store = db.get_store("sqlite:")
        # Read schema from file
        with io.open('schema/sqlite.sql', 'r') as sql:
            schema = sql.read()
            # Create tables on memory database
            for command in schema.split(';'):
                self.store.execute(command)

        # Create some users
        self.assertEqual(UserManager.add(self.store, 'alice', 'ALICE', 'test@example.com', True), UserManager.SUCCESS)
        self.assertEqual(UserManager.add(self.store, 'bob', 'BOB', 'bob@example.com', False), UserManager.SUCCESS)
        self.assertEqual(UserManager.add(self.store, 'charlie', 'CHARLIE', 'charlie@example.com', False), UserManager.SUCCESS)

        folder = db.Folder()
        folder.name = 'Root'
        folder.path = 'tests/assets'
        folder.root = True

        artist = db.Artist()
        artist.name = 'Artist'

        album = db.Album()
        album.name = 'Album'
        album.artist = artist

        track = db.Track()
        track.title = 'Track'
        track.disc = 1
        track.number = 1
        track.duration = 1
        track.artist = artist
        track.album = album
        track.path = 'tests/assets/empty'
        track.folder = folder
        track.root_folder = folder
        track.duration = 2
        track.content_type = 'audio/mpeg'
        track.bitrate = 320
        track.last_modification = 0
        self.store.add(track)
        self.store.commit()

        playlist = db.Playlist()
        playlist.name = 'Playlist'
        playlist.user = self.store.find(db.User, db.User.name == 'alice').one()
        playlist.add(track)
        self.store.add(playlist)
        self.store.commit()

    def test_encrypt_password(self):
        func = UserManager._UserManager__encrypt_password
        self.assertEqual(func(u'password',u'salt'), (u'59b3e8d637cf97edbe2384cf59cb7453dfe30789', u'salt'))
        self.assertEqual(func(u'pass-word',u'pepper'), (u'd68c95a91ed7773aa57c7c044d2309a5bf1da2e7', u'pepper'))
        self.assertEqual(func(u'éèàïô', u'ABC+'), (u'b639ba5217b89c906019d89d5816b407d8730898', u'ABC+'))

    def test_get_user(self):
        # Get existing users
        for name in ['alice', 'bob', 'charlie']:
            user = self.store.find(db.User, db.User.name == name).one()
            self.assertEqual(UserManager.get(self.store, user.id), (UserManager.SUCCESS, user))

        # Get with invalid UUID
        self.assertEqual(UserManager.get(self.store, 'invalid-uuid'), (UserManager.INVALID_ID, None))
        self.assertEqual(UserManager.get(self.store, 0xfee1bad), (UserManager.INVALID_ID, None))

        # Non-existent user
        self.assertEqual(UserManager.get(self.store, uuid.uuid4()), (UserManager.NO_SUCH_USER, None))

    def test_add_user(self):
        # Added in setUp()
        self.assertEqual(self.store.find(db.User).count(), 3)

        # Create duplicate
        self.assertEqual(UserManager.add(self.store, 'alice', 'Alic3', 'alice@example.com', True), UserManager.NAME_EXISTS)

    def test_delete_user(self):
        # Delete invalid UUID
        self.assertEqual(UserManager.delete(self.store, 'invalid-uuid'), UserManager.INVALID_ID)
        self.assertEqual(UserManager.delete(self.store, 0xfee1b4d), UserManager.INVALID_ID)
        self.assertEqual(self.store.find(db.User).count(), 3)

        # Delete non-existent user
        self.assertEqual(UserManager.delete(self.store, uuid.uuid4()), UserManager.NO_SUCH_USER)
        self.assertEqual(self.store.find(db.User).count(), 3)

        # Delete existing users
        for name in ['alice', 'bob', 'charlie']:
            user = self.store.find(db.User, db.User.name == name).one()
            self.assertEqual(UserManager.delete(self.store, user.id), UserManager.SUCCESS)
            self.assertIsNone(self.store.get(db.User, user.id))
        self.assertEqual(self.store.find(db.User).count(), 0)

    def test_delete_by_name(self):
        # Delete existing users
        for name in ['alice', 'bob', 'charlie']:
            self.assertEqual(UserManager.delete_by_name(self.store, name), UserManager.SUCCESS)
            self.assertEqual(self.store.find(db.User, db.User.name == name).count(), 0)

        # Delete non-existent user
        self.assertEqual(UserManager.delete_by_name(self.store, 'null'), UserManager.NO_SUCH_USER)

    def test_try_auth(self):
        # Test authentication
        for name in ['alice', 'bob', 'charlie']:
            user = self.store.find(db.User, db.User.name == name).one()
            self.assertEqual(UserManager.try_auth(self.store, name, name.upper()), (UserManager.SUCCESS, user))

        # Wrong password
        self.assertEqual(UserManager.try_auth(self.store, 'alice', 'bad'), (UserManager.WRONG_PASS, None))
        self.assertEqual(UserManager.try_auth(self.store, 'alice', 'alice'), (UserManager.WRONG_PASS, None))

        # Non-existent user
        self.assertEqual(UserManager.try_auth(self.store, 'null', 'null'), (UserManager.NO_SUCH_USER, None))

    def test_change_password(self):
        # With existing users
        for name in ['alice', 'bob', 'charlie']:
            user = self.store.find(db.User, db.User.name == name).one()
            # Good password
            self.assertEqual(UserManager.change_password(self.store, user.id, name.upper(), 'newpass'), UserManager.SUCCESS)
            self.assertEqual(UserManager.try_auth(self.store, name, 'newpass'), (UserManager.SUCCESS, user))
            # Old password
            self.assertEqual(UserManager.try_auth(self.store, name, name.upper()), (UserManager.WRONG_PASS, None))
            # Wrong password
            self.assertEqual(UserManager.change_password(self.store, user.id, 'badpass', 'newpass'), UserManager.WRONG_PASS)

        # Ensure we still got the same number of users
        self.assertEqual(self.store.find(db.User).count(), 3)

        # With invalid UUID
        self.assertEqual(UserManager.change_password(self.store, 'invalid-uuid', 'oldpass', 'newpass'), UserManager.INVALID_ID)

        # Non-existent user
        self.assertEqual(UserManager.change_password(self.store, uuid.uuid4(), 'oldpass', 'newpass'), UserManager.NO_SUCH_USER)

    def test_change_password2(self):
        # With existing users
        for name in ['alice', 'bob', 'charlie']:
            self.assertEqual(UserManager.change_password2(self.store, name, 'newpass'), UserManager.SUCCESS)
            user = self.store.find(db.User, db.User.name == name).one()
            self.assertEqual(UserManager.try_auth(self.store, name, 'newpass'), (UserManager.SUCCESS, user))
            self.assertEqual(UserManager.try_auth(self.store, name, name.upper()), (UserManager.WRONG_PASS, None))

        # Non-existent user
        self.assertEqual(UserManager.change_password2(self.store, 'null', 'newpass'), UserManager.NO_SUCH_USER)

    def test_human_readable_error(self):
        values = [ UserManager.SUCCESS, UserManager.INVALID_ID, UserManager.NO_SUCH_USER, UserManager.NAME_EXISTS,
            UserManager.WRONG_PASS, 1594826, 'string', uuid.uuid4() ]
        for value in values:
            self.assertIsInstance(UserManager.error_str(value), basestring)

if __name__ == '__main__':
    unittest.main()


#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

from supysonic import db
from supysonic.managers.user import UserManager
from supysonic.py23 import strtype

import io
import unittest
import uuid

from pony.orm import db_session, commit
from pony.orm import ObjectNotFound

class UserManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory
        db.init_database('sqlite:', True)

    def tearDown(self):
        db.release_database()

    @db_session
    def create_data(self):
        # Create some users
        self.assertEqual(UserManager.add('alice', 'ALICE', 'test@example.com', True), UserManager.SUCCESS)
        self.assertEqual(UserManager.add('bob', 'BOB', 'bob@example.com', False), UserManager.SUCCESS)
        self.assertEqual(UserManager.add('charlie', 'CHARLIE', 'charlie@example.com', False), UserManager.SUCCESS)

        folder = db.Folder(name = 'Root', path = 'tests/assets', root = True)
        artist = db.Artist(name = 'Artist')
        album = db.Album(name = 'Album', artist = artist)
        track = db.Track(
            title = 'Track',
            disc = 1,
            number = 1,
            duration = 1,
            artist = artist,
            album = album,
            path = 'tests/assets/empty',
            folder = folder,
            root_folder = folder,
            content_type = 'audio/mpeg',
            bitrate = 320,
            last_modification = 0
        )

        playlist = db.Playlist(
            name = 'Playlist',
            user = db.User.get(name = 'alice')
        )
        playlist.add(track)

    def test_encrypt_password(self):
        func = UserManager._UserManager__encrypt_password
        self.assertEqual(func(u'password',u'salt'), (u'59b3e8d637cf97edbe2384cf59cb7453dfe30789', u'salt'))
        self.assertEqual(func(u'pass-word',u'pepper'), (u'd68c95a91ed7773aa57c7c044d2309a5bf1da2e7', u'pepper'))
        self.assertEqual(func(u'éèàïô', u'ABC+'), (u'b639ba5217b89c906019d89d5816b407d8730898', u'ABC+'))

    @db_session
    def test_get_user(self):
        self.create_data()

        # Get existing users
        for name in ['alice', 'bob', 'charlie']:
            user = db.User.get(name = name)
            self.assertEqual(UserManager.get(user.id), (UserManager.SUCCESS, user))

        # Get with invalid UUID
        self.assertEqual(UserManager.get('invalid-uuid'), (UserManager.INVALID_ID, None))
        self.assertEqual(UserManager.get(0xfee1bad), (UserManager.INVALID_ID, None))

        # Non-existent user
        self.assertEqual(UserManager.get(uuid.uuid4()), (UserManager.NO_SUCH_USER, None))

    @db_session
    def test_add_user(self):
        self.create_data()
        self.assertEqual(db.User.select().count(), 3)

        # Create duplicate
        self.assertEqual(UserManager.add('alice', 'Alic3', 'alice@example.com', True), UserManager.NAME_EXISTS)

    @db_session
    def test_delete_user(self):
        self.create_data()

        # Delete invalid UUID
        self.assertEqual(UserManager.delete('invalid-uuid'), UserManager.INVALID_ID)
        self.assertEqual(UserManager.delete(0xfee1b4d), UserManager.INVALID_ID)
        self.assertEqual(db.User.select().count(), 3)

        # Delete non-existent user
        self.assertEqual(UserManager.delete(uuid.uuid4()), UserManager.NO_SUCH_USER)
        self.assertEqual(db.User.select().count(), 3)

        # Delete existing users
        for name in ['alice', 'bob', 'charlie']:
            user = db.User.get(name = name)
            self.assertEqual(UserManager.delete(user.id), UserManager.SUCCESS)
            self.assertRaises(ObjectNotFound, db.User.__getitem__, user.id)
        commit()
        self.assertEqual(db.User.select().count(), 0)

    @db_session
    def test_delete_by_name(self):
        self.create_data()

        # Delete existing users
        for name in ['alice', 'bob', 'charlie']:
            self.assertEqual(UserManager.delete_by_name(name), UserManager.SUCCESS)
            self.assertFalse(db.User.exists(name = name))

        # Delete non-existent user
        self.assertEqual(UserManager.delete_by_name('null'), UserManager.NO_SUCH_USER)

    @db_session
    def test_try_auth(self):
        self.create_data()

        # Test authentication
        for name in ['alice', 'bob', 'charlie']:
            user = db.User.get(name = name)
            self.assertEqual(UserManager.try_auth(name, name.upper()), (UserManager.SUCCESS, user))

        # Wrong password
        self.assertEqual(UserManager.try_auth('alice', 'bad'), (UserManager.WRONG_PASS, None))
        self.assertEqual(UserManager.try_auth('alice', 'alice'), (UserManager.WRONG_PASS, None))

        # Non-existent user
        self.assertEqual(UserManager.try_auth('null', 'null'), (UserManager.NO_SUCH_USER, None))

    @db_session
    def test_change_password(self):
        self.create_data()

        # With existing users
        for name in ['alice', 'bob', 'charlie']:
            user = db.User.get(name = name)
            # Good password
            self.assertEqual(UserManager.change_password(user.id, name.upper(), 'newpass'), UserManager.SUCCESS)
            self.assertEqual(UserManager.try_auth(name, 'newpass'), (UserManager.SUCCESS, user))
            # Old password
            self.assertEqual(UserManager.try_auth(name, name.upper()), (UserManager.WRONG_PASS, None))
            # Wrong password
            self.assertEqual(UserManager.change_password(user.id, 'badpass', 'newpass'), UserManager.WRONG_PASS)

        # Ensure we still got the same number of users
        self.assertEqual(db.User.select().count(), 3)

        # With invalid UUID
        self.assertEqual(UserManager.change_password('invalid-uuid', 'oldpass', 'newpass'), UserManager.INVALID_ID)

        # Non-existent user
        self.assertEqual(UserManager.change_password(uuid.uuid4(), 'oldpass', 'newpass'), UserManager.NO_SUCH_USER)

    @db_session
    def test_change_password2(self):
        self.create_data()

        # With existing users
        for name in ['alice', 'bob', 'charlie']:
            self.assertEqual(UserManager.change_password2(name, 'newpass'), UserManager.SUCCESS)
            user = db.User.get(name = name)
            self.assertEqual(UserManager.try_auth(name, 'newpass'), (UserManager.SUCCESS, user))
            self.assertEqual(UserManager.try_auth(name, name.upper()), (UserManager.WRONG_PASS, None))

        # Non-existent user
        self.assertEqual(UserManager.change_password2('null', 'newpass'), UserManager.NO_SUCH_USER)

    def test_human_readable_error(self):
        values = [ UserManager.SUCCESS, UserManager.INVALID_ID, UserManager.NO_SUCH_USER, UserManager.NAME_EXISTS,
            UserManager.WRONG_PASS, 1594826, 'string', uuid.uuid4() ]
        for value in values:
            self.assertIsInstance(UserManager.error_str(value), strtype)

if __name__ == '__main__':
    unittest.main()


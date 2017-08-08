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

class UserManagerTestCase(unittest.TestCase):
    def setUp(self):
        # Create an empty sqlite database in memory
        self.store = db.get_store("sqlite:")
        # Read schema from file
        with open('schema/sqlite.sql') as sql:
            schema = sql.read()
        # Create tables on memory database
        for command in schema.split(';'):
            self.store.execute(command)
        # Create some users
        self.assertEqual(UserManager.add(self.store, 'alice', 'alice', 'test@example.com', True), UserManager.SUCCESS)
        self.assertEqual(UserManager.add(self.store, 'bob', 'bob', 'bob@example.com', False), UserManager.SUCCESS)
        self.assertEqual(UserManager.add(self.store, 'charlie', 'charlie', 'charlie@example.com', False), UserManager.SUCCESS)

    def test_encrypt_password(self):
        self.assertEqual(UserManager._UserManager__encrypt_password('password','salt'), ('59b3e8d637cf97edbe2384cf59cb7453dfe30789', 'salt'))
        self.assertEqual(UserManager._UserManager__encrypt_password('pass-word','pepper'), ('d68c95a91ed7773aa57c7c044d2309a5bf1da2e7', 'pepper'))

    def test_get_user(self):
        # Get existing users
        for name in ['alice', 'bob', 'charlie']:
            user = self.store.find(db.User, db.User.name == name).one()
            self.assertEqual(UserManager.get(self.store, user.id), (UserManager.SUCCESS, user))
        # Get with invalid UUID
        self.assertEqual(UserManager.get(self.store, 'invalid-uuid'), (UserManager.INVALID_ID, None))
        # Non-existent user
        self.assertEqual(UserManager.get(self.store, uuid.uuid4()), (UserManager.NO_SUCH_USER, None))

    def test_add_user(self):
        # Create duplicate
        self.assertEqual(UserManager.add(self.store, 'alice', 'alice', 'test@example.com', True), UserManager.NAME_EXISTS)

    def test_delete_user(self):
        # Delete existing users
        for name in ['alice', 'bob', 'charlie']:
            user = self.store.find(db.User, db.User.name == name).one()
            self.assertEqual(UserManager.delete(self.store, user.id), UserManager.SUCCESS)
        # Delete invalid UUID
        self.assertEqual(UserManager.delete(self.store, 'invalid-uuid'), UserManager.INVALID_ID)
        # Delete non-existent user
        self.assertEqual(UserManager.delete(self.store, uuid.uuid4()), UserManager.NO_SUCH_USER)

    def test_try_auth(self):
        # Test authentication
        for name in ['alice', 'bob', 'charlie']:
            user = self.store.find(db.User, db.User.name == name).one()
            self.assertEqual(UserManager.try_auth(self.store, name, name), (UserManager.SUCCESS, user))
        # Wrong password
        self.assertEqual(UserManager.try_auth(self.store, name, 'bad'), (UserManager.WRONG_PASS, None))
        # Non-existent user
        self.assertEqual(UserManager.try_auth(self.store, 'null', 'null'), (UserManager.NO_SUCH_USER, None))

    def test_change_password(self):
        # With existing users
        for name in ['alice', 'bob', 'charlie']:
            user = self.store.find(db.User, db.User.name == name).one()
            # God password
            self.assertEqual(UserManager.change_password(self.store, user.id, name, 'newpass'), UserManager.SUCCESS)
            self.assertEqual(UserManager.try_auth(self.store, name, 'newpass'), (UserManager.SUCCESS, user))
            # Wrong password
            self.assertEqual(UserManager.change_password(self.store, user.id, 'badpass', 'newpass'), UserManager.WRONG_PASS)
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
        # Non-existent user
        self.assertEqual(UserManager.change_password2(self.store, 'null', 'newpass'), UserManager.NO_SUCH_USER)

if __name__ == '__main__':
    unittest.main()

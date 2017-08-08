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

import sys
import unittest
import uuid

# Create an empty sqlite database in memory
store = db.get_store("sqlite:")
# Read schema from file
with open('schema/sqlite.sql') as sql:
    schema = sql.read()
# Create tables on memory database
for command in schema.split(';'):
    store.execute(command)
# Create some users
UserManager.add(store, 'alice', 'alice', 'test@example.com', True)
UserManager.add(store, 'bob', 'bob', 'bob@example.com', False)
UserManager.add(store, 'charlie', 'charlie', 'charlie@example.com', False)

# Create a mockup of web
from flask import Flask
app = Flask(__name__, template_folder='../supysonic/templates')
class web():
    app = app
    store = store
sys.modules['supysonic.web'] = web()

# Import module and set app in test mode
import supysonic.frontend
app.secret_key = 'test-suite'

class FrontendTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_unauthorized_request(self):
        # Unauthorized request
        rv = self.app.get('/', follow_redirects=True)
        self.assertIn('Please login', rv.data)

    def test_login_with_bad_data(self):
        # Login with not blank user or password
        rv = self.app.post('/user/login', data=dict(name='', password=''), follow_redirects=True)
        self.assertIn('Missing user name', rv.data)
        self.assertIn('Missing password', rv.data)
        # Login with not valid user or password
        rv = self.app.post('/user/login', data=dict(user='nonexistent', password='nonexistent'), follow_redirects=True)
        self.assertIn('No such user', rv.data)
        rv = self.app.post('/user/login', data=dict(user='alice', password='badpassword'), follow_redirects=True)
        self.assertIn('Wrong password', rv.data)

    def test_login_admin(self):
        # Login with a valid admin user
        rv = self.app.post('/user/login', data=dict(user='alice', password='alice'), follow_redirects=True)
        self.assertIn('Logged in', rv.data)
        self.assertIn('Users', rv.data)
        self.assertIn('Folders', rv.data)

    def test_login_non_admin(self):
        # Login with a valid non-admin user
        rv = self.app.post('/user/login', data=dict(user='bob', password='bob'), follow_redirects=True)
        self.assertIn('Logged in', rv.data)
        # Non-admin user cannot acces to users and folders
        self.assertNotIn('Users', rv.data)
        self.assertNotIn('Folders', rv.data)

    def test_root_with_valid_session(self):
        # Root with valid session
        with self.app.session_transaction() as sess:
            sess['userid'] = store.find(db.User, db.User.name == 'alice').one().id
            sess['username'] = 'alice'
        rv = self.app.get('/', follow_redirects=True)
        self.assertIn('alice', rv.data)
        self.assertIn('Log out', rv.data)
        self.assertIn('There\'s nothing much to see here.', rv.data)

    def test_root_with_non_valid_session(self):
        # Root with a no-valid session
        with self.app.session_transaction() as sess:
            sess['userid'] = uuid.uuid4()
            sess['username'] = 'alice'
        rv = self.app.get('/', follow_redirects=True)
        self.assertIn('Please login', rv.data)
        # Root with a no-valid user
        with self.app.session_transaction() as sess:
            sess['userid'] = store.find(db.User, db.User.name == 'alice').one().id
            sess['username'] = 'nonexistent'
        rv = self.app.get('/', follow_redirects=True)
        self.assertIn('Please login', rv.data)

if __name__ == '__main__':
    unittest.main()

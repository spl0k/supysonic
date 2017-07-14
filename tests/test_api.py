#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Óscar García Amor <ogarcia@connectical.com>
#
# Distributed under terms of the GNU GPLv3 license.

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
app = Flask(__name__)
class web():
    app = app
    store = store
sys.modules['supysonic.web'] = web()

# Import module and set app in test mode
#from supysonic.api import user
import supysonic.api

class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_user_info(self):
        # Missing username
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test')
        assert 'message="Missing username"' in rv.data
        # Non-admin request for other user
        rv = self.app.get('/rest/getUser.view?u=bob&p=bob&c=test&username=alice')
        assert 'message="Admin restricted"' in rv.data
        # Non-existent user
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test&username=null')
        assert 'message="Unknown user"' in rv.data
        # Admin request
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test&username=alice')
        assert 'adminRole="true"' in rv.data
        # Non-admin request
        rv = self.app.get('/rest/getUser.view?u=bob&p=bob&c=test&username=bob')
        assert 'adminRole="false"' in rv.data

    def test_get_users(self):
        rv = self.app.get('/rest/getUsers.view?u=alice&p=alice&c=test')
        print rv.data

if __name__ == '__main__':
    unittest.main()

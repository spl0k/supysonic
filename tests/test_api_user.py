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

class ApiUserTestCase(unittest.TestCase):
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
        # Create a mockup of web
        from flask import Flask
        self.app = Flask(__name__)
        class web():
            app = self.app
            store = self.store
        sys.modules['supysonic.web'] = web()
        # Import module and set app in test mode
        from supysonic.api.user import user_info
        self.app.testing = True
        self.app = self.app.test_client()

    def test_user_info(self):
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test')
        assert 'message="Missing username"' in rv.data
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test&username=alice')
        assert 'adminRole="true"' in rv.data

if __name__ == '__main__':
    unittest.main()

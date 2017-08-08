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
app = Flask(__name__)
class web():
    app = app
    store = store
sys.modules['supysonic.web'] = web()

# Import module and set app in test mode
import supysonic.api

class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_ping(self):
        # GET non-existent user
        rv = self.app.get('/rest/ping.view?u=null&p=null&c=test')
        self.assertIn('status="failed"', rv.data)
        self.assertIn('message="Unauthorized"', rv.data)
        # POST non-existent user
        rv = self.app.post('/rest/ping.view', data=dict(u='null', p='null', c='test'))
        self.assertIn('status="failed"', rv.data)
        self.assertIn('message="Unauthorized"', rv.data)
        # GET user request
        rv = self.app.get('/rest/ping.view?u=alice&p=alice&c=test')
        self.assertIn('status="ok"', rv.data)
        # POST user request
        rv = self.app.post('/rest/ping.view', data=dict(u='alice', p='alice', c='test'))
        self.assertIn('status="ok"', rv.data)
        # GET user request with old enc:
        rv = self.app.get('/rest/ping.view?u=alice&p=enc:616c696365&c=test')
        self.assertIn('status="ok"', rv.data)
        # POST user request with old enc:
        rv = self.app.post('/rest/ping.view', data=dict(u='alice', p='enc:616c696365', c='test'))
        self.assertIn('status="ok"', rv.data)
        # GET user request with bad password
        rv = self.app.get('/rest/ping.view?u=alice&p=bad&c=test')
        self.assertIn('status="failed"', rv.data)
        self.assertIn('message="Unauthorized"', rv.data)
        # POST user request with bad password
        rv = self.app.post('/rest/ping.view', data=dict(u='alice', p='bad', c='test'))
        self.assertIn('status="failed"', rv.data)
        self.assertIn('message="Unauthorized"', rv.data)

    def test_ping_in_jsonp(self):
        # If ping in jsonp works all other endpoints must work OK
        # GET non-existent user
        rv = self.app.get('/rest/ping.view?u=null&p=null&c=test&f=jsonp&callback=test')
        self.assertIn('"status": "failed"', rv.data)
        self.assertIn('"message": "Unauthorized"', rv.data)
        # POST non-existent user
        rv = self.app.post('/rest/ping.view', data=dict(u='null', p='null', c='test', f='jsonp', callback='test'))
        self.assertIn('"status": "failed"', rv.data)
        self.assertIn('"message": "Unauthorized"', rv.data)
        # GET user request
        rv = self.app.get('/rest/ping.view?u=alice&p=alice&c=test&f=jsonp&callback=test')
        self.assertIn('"status": "ok"', rv.data)
        # POST user request
        rv = self.app.post('/rest/ping.view', data=dict(u='alice', p='alice', c='test', f='jsonp', callback='test'))
        self.assertIn('"status": "ok"', rv.data)
        # GET user request with bad password
        rv = self.app.get('/rest/ping.view?u=alice&p=bad&c=test&f=jsonp&callback=test')
        self.assertIn('"status": "failed"', rv.data)
        self.assertIn('"message": "Unauthorized"', rv.data)
        # POST user request with bad password
        rv = self.app.post('/rest/ping.view', data=dict(u='alice', p='bad', c='test', f='jsonp', callback='test'))
        self.assertIn('"status": "failed"', rv.data)
        self.assertIn('"message": "Unauthorized"', rv.data)

    def test_not_implemented(self):
        # Access to not implemented endpoint
        rv = self.app.get('/rest/not-implemented?u=alice&p=alice&c=test')
        self.assertIn('message="Not implemented"', rv.data)
        rv = self.app.post('/rest/not-implemented', data=dict(u='alice', p='alice', c='test'))
        self.assertIn('message="Not implemented"', rv.data)

    def test_get_license(self):
        # GET user request
        rv = self.app.get('/rest/getLicense.view?u=alice&p=alice&c=test')
        self.assertIn('status="ok"', rv.data)
        self.assertIn('license valid="true"', rv.data)
        # POST user request
        rv = self.app.post('/rest/getLicense.view', data=dict(u='alice', p='alice', c='test'))
        self.assertIn('status="ok"', rv.data)
        self.assertIn('license valid="true"', rv.data)

    def test_get_user(self):
        # GET missing username
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test')
        self.assertIn('message="Missing username"', rv.data)
        # POST missing username
        rv = self.app.post('/rest/getUser.view', data=dict(u='alice', p='alice', c='test'))
        self.assertIn('message="Missing username"', rv.data)
        # GET non-admin request for other user
        rv = self.app.get('/rest/getUser.view?u=bob&p=bob&c=test&username=alice')
        self.assertIn('message="Admin restricted"', rv.data)
        # POST non-admin request for other user
        rv = self.app.post('/rest/getUser.view', data=dict(u='bob', p='bob', c='test', username='alice'))
        self.assertIn('message="Admin restricted"', rv.data)
        # GET non-existent user
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test&username=null')
        self.assertIn('message="Unknown user"', rv.data)
        # POST non-existent user
        rv = self.app.post('/rest/getUser.view', data=dict(u='alice', p='alice', c='test', username='null'))
        self.assertIn('message="Unknown user"', rv.data)
        # GET admin request
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test&username=alice')
        self.assertIn('adminRole="true"', rv.data)
        self.assertIn('username="alice"', rv.data)
        # POST admin request
        rv = self.app.post('/rest/getUser.view', data=dict(u='alice', p='alice', c='test', username='alice'))
        self.assertIn('adminRole="true"', rv.data)
        self.assertIn('username="alice"', rv.data)
        # GET admin request for other user
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test&username=bob')
        self.assertIn('username="bob"', rv.data)
        self.assertIn('adminRole="false"', rv.data)
        # POST admin request for other user
        rv = self.app.post('/rest/getUser.view', data=dict(u='alice', p='alice', c='test', username='bob'))
        self.assertIn('username="bob"', rv.data)
        self.assertIn('adminRole="false"', rv.data)
        # GET non-admin request
        rv = self.app.get('/rest/getUser.view?u=charlie&p=charlie&c=test&username=charlie')
        self.assertIn('username="charlie"', rv.data)
        self.assertIn('adminRole="false"', rv.data)
        # POST non-admin request
        rv = self.app.post('/rest/getUser.view', data=dict(u='charlie', p='charlie', c='test', username='charlie'))
        self.assertIn('username="charlie"', rv.data)
        self.assertIn('adminRole="false"', rv.data)

    def test_get_users(self):
        # GET admin request
        rv = self.app.get('/rest/getUsers.view?u=alice&p=alice&c=test')
        self.assertIn('alice', rv.data)
        self.assertIn('bob', rv.data)
        self.assertIn('charlie', rv.data)
        # POST admin request
        rv = self.app.post('/rest/getUsers.view', data=dict(u='alice', p='alice', c='test'))
        self.assertIn('alice', rv.data)
        self.assertIn('bob', rv.data)
        self.assertIn('charlie', rv.data)
        # GET non-admin request
        rv = self.app.get('/rest/getUsers.view?u=bob&p=bob&c=test')
        self.assertIn('message="Admin restricted"', rv.data)
        # POST non-admin request
        rv = self.app.post('/rest/getUsers.view', data=dict(u='bob', p='bob', c='test'))
        self.assertIn('message="Admin restricted"', rv.data)

    def test_create_user(self):
        # GET non-admin request
        rv = self.app.get('/rest/createUser.view?u=bob&p=bob&c=test')
        self.assertIn('message="Admin restricted"', rv.data)
        # POST non-admin request
        rv = self.app.post('/rest/createUser.view', data=dict(u='bob', p='bob', c='test'))
        self.assertIn('message="Admin restricted"', rv.data)
        # GET incomplete request
        rv = self.app.get('/rest/createUser.view?u=alice&p=alice&c=test')
        self.assertIn('message="Missing parameter"', rv.data)
        # POST incomplete request
        rv = self.app.post('/rest/createUser.view', data=dict(u='alice', p='alice', c='test'))
        self.assertIn('message="Missing parameter"', rv.data)
        # GET create user and test that user is created
        rv = self.app.get('/rest/createUser.view?u=alice&p=alice&c=test&username=david&password=david&email=david%40example.com&adminRole=True')
        self.assertIn('status="ok"', rv.data)
        rv = self.app.get('/rest/getUser.view?u=david&p=david&c=test&username=david')
        self.assertIn('username="david"', rv.data)
        self.assertIn('email="david@example.com"', rv.data)
        self.assertIn('adminRole="true"', rv.data)
        # POST create user and test that user is created
        rv = self.app.post('/rest/createUser.view', data=dict(u='alice', p='alice', c='test', username='elanor', password='elanor', email='elanor@example.com', adminRole=True))
        self.assertIn('status="ok"', rv.data)
        rv = self.app.post('/rest/getUser.view', data=dict(u='elanor', p='elanor', c='test', username='elanor'))
        self.assertIn('username="elanor"', rv.data)
        self.assertIn('email="elanor@example.com"', rv.data)
        self.assertIn('adminRole="true"', rv.data)
        # GET create duplicate
        rv = self.app.get('/rest/createUser.view?u=alice&p=alice&c=test&username=david&password=david&email=david%40example.com&adminRole=True')
        self.assertIn('message="There is already a user with that username"', rv.data)
        # POST create duplicate
        rv = self.app.post('/rest/createUser.view', data=dict(u='alice', p='alice', c='test', username='elanor', password='elanor', email='elanor@example.com', adminRole=True))
        self.assertIn('message="There is already a user with that username"', rv.data)

    def test_delete_user(self):
        # GET non-admin request
        rv = self.app.get('/rest/deleteUser.view?u=bob&p=bob&c=test')
        self.assertIn('message="Admin restricted"', rv.data)
        # POST non-admin request
        rv = self.app.post('/rest/deleteUser.view', data=dict(u='bob', p='bob', c='test'))
        self.assertIn('message="Admin restricted"', rv.data)
        # GET incomplete request
        rv = self.app.get('/rest/deleteUser.view?u=alice&p=alice&c=test')
        self.assertIn('message="Unknown user"', rv.data)
        # POST incomplete request
        rv = self.app.post('/rest/deleteUser.view', data=dict(u='alice', p='alice', c='test'))
        self.assertIn('message="Unknown user"', rv.data)
        # GET delete non-existent user
        rv = self.app.get('/rest/deleteUser.view?u=alice&p=alice&c=test&username=nonexistent')
        self.assertIn('message="Unknown user"', rv.data)
        # POST delete non-existent user
        rv = self.app.post('/rest/deleteUser.view', data=dict(u='alice', p='alice', c='test', username='nonexistent'))
        self.assertIn('message="Unknown user"', rv.data)
        # GET delete existent user
        rv = self.app.get('/rest/deleteUser.view?u=alice&p=alice&c=test&username=elanor')
        self.assertIn('status="ok"', rv.data)
        rv = self.app.get('/rest/getUser.view?u=alice&p=alice&c=test&username=elanor')
        self.assertIn('message="Unknown user"', rv.data)
        # POST delete existent user
        rv = self.app.post('/rest/deleteUser.view', data=dict(u='alice', p='alice', c='test', username='david'))
        self.assertIn('status="ok"', rv.data)
        rv = self.app.post('/rest/getUser.view', data=dict(u='alice', p='alice', c='test', username='david'))
        self.assertIn('message="Unknown user"', rv.data)

    def test_change_password(self):
        # GET incomplete request
        rv = self.app.get('/rest/changePassword.view?u=alice&p=alice&c=test')
        self.assertIn('message="Missing parameter"', rv.data)
        # POST incomplete request
        rv = self.app.post('/rest/changePassword.view', data=dict(u='alice', p='alice', c='test'))
        self.assertIn('message="Missing parameter"', rv.data)
        # GET non-admin change own password
        rv = self.app.get('/rest/changePassword.view?u=bob&p=bob&c=test&username=bob&password=newpassword')
        self.assertIn('status="ok"', rv.data)
        # POST non-admin change own password
        rv = self.app.post('/rest/changePassword.view', data=dict(u='bob', p='newpassword', c='test', username='bob', password='bob'))
        self.assertIn('status="ok"', rv.data)
        # GET non-admin change other user password
        rv = self.app.get('/rest/changePassword.view?u=bob&p=bob&c=test&username=alice&password=newpassword')
        self.assertIn('message="Admin restricted"', rv.data)
        # POST non-admin change other user password
        rv = self.app.post('/rest/changePassword.view', data=dict(u='bob', p='bob', c='test', username='alice', password='newpassword'))
        self.assertIn('message="Admin restricted"', rv.data)
        # GET admin change other user password
        rv = self.app.get('/rest/changePassword.view?u=bob&p=bob&c=test&username=bob&password=newpassword')
        self.assertIn('status="ok"', rv.data)
        # POST admin change other user password
        rv = self.app.post('/rest/changePassword.view', data=dict(u='bob', p='newpassword', c='test', username='bob', password='bob'))
        self.assertIn('status="ok"', rv.data)
        # GET change non-existent user password
        rv = self.app.get('/rest/changePassword.view?u=alice&p=alice&c=test&username=nonexistent&password=nonexistent')
        self.assertIn('message="No such user"', rv.data)
        # POST change non-existent user password
        rv = self.app.post('/rest/changePassword.view', data=dict(u='alice', p='alice', c='test', username='nonexistent', password='nonexistent'))
        self.assertIn('message="No such user"', rv.data)
        # GET non-admin change own password using extended utf-8 characters
        rv = self.app.get('/rest/changePassword.view?u=bob&p=bob&c=test&username=bob&password=новыйпароль')
        self.assertIn('status="ok"', rv.data)
        # POST non-admin change own password using extended utf-8 characters
        rv = self.app.post('/rest/changePassword.view', data=dict(u='bob', p='новыйпароль', c='test', username='bob', password='bob'))
        self.assertIn('status="ok"', rv.data)
        # GET non-admin change own password using extended utf-8 characters with old enc:
        rv = self.app.get('/rest/changePassword.view?u=bob&p=enc:626f62&c=test&username=bob&password=новыйпароль')
        self.assertIn('status="ok"', rv.data)
        # POST non-admin change own password using extended utf-8 characters with old enc:
        rv = self.app.post('/rest/changePassword.view', data=dict(u='bob', p='enc:d0bdd0bed0b2d18bd0b9d0bfd0b0d180d0bed0bbd18c', c='test', username='bob', password='bob'))
        self.assertIn('status="ok"', rv.data)
        # GET non-admin change own password using enc: in password
        rv = self.app.get('/rest/changePassword.view?u=bob&p=bob&c=test&username=bob&password=enc:test')
        self.assertIn('status="ok"', rv.data)
        # POST non-admin change own password using enc: in password
        rv = self.app.post('/rest/changePassword.view', data=dict(u='bob', p='enc:test', c='test', username='bob', password='bob'))
        self.assertIn('status="ok"', rv.data)

if __name__ == '__main__':
    unittest.main()

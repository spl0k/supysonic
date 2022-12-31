# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import uuid

from supysonic.db import User

from .frontendtestbase import FrontendTestBase


class LoginTestCase(FrontendTestBase):
    def test_unauthorized_request(self):
        # Unauthorized request
        rv = self.client.get("/", follow_redirects=True)
        self.assertIn("Please login", rv.data)

    def test_login_with_bad_data(self):
        # Login with not blank user or password
        rv = self._login("", "")
        self.assertIn("Missing user name", rv.data)
        self.assertIn("Missing password", rv.data)
        # Login with not valid user or password
        rv = self._login("nonexistent", "nonexistent")
        self.assertIn("Wrong username or password", rv.data)
        rv = self._login("alice", "badpassword")
        self.assertIn("Wrong username or password", rv.data)

    def test_login_admin(self):
        # Login with a valid admin user
        rv = self._login("alice", "Alic3")
        self.assertIn("Logged in", rv.data)
        self.assertIn("Users", rv.data)
        self.assertIn("Folders", rv.data)

    def test_login_non_admin(self):
        # Login with a valid non-admin user
        rv = self._login("bob", "B0b")
        self.assertIn("Logged in", rv.data)
        # Non-admin user cannot acces to users and folders
        self.assertNotIn("Users", rv.data)
        self.assertNotIn("Folders", rv.data)

    def test_root_with_valid_session(self):
        # Root with valid session
        with self.client.session_transaction() as sess:
            sess["userid"] = User.get(name="alice").id
        rv = self.client.get("/", follow_redirects=True)
        self.assertIn("alice", rv.data)
        self.assertIn("Log out", rv.data)
        self.assertIn("There's nothing much to see here.", rv.data)

    def test_root_with_non_valid_session(self):
        # Root with a no-valid session
        with self.client.session_transaction() as sess:
            sess["userid"] = uuid.uuid4()
        rv = self.client.get("/", follow_redirects=True)
        self.assertIn("Please login", rv.data)

    def test_multiple_login(self):
        self._login("alice", "Alic3")
        rv = self._login("bob", "B0b")
        self.assertIn("Already logged in", rv.data)
        self.assertIn("alice", rv.data)


if __name__ == "__main__":
    unittest.main()

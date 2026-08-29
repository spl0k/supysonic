# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import html
import unittest
import uuid
from unittest.mock import Mock, patch

from supysonic.db import ClientPrefs, User

from .frontendtestbase import FrontendTestBase


class UserTestCase(FrontendTestBase):
    def setUp(self):
        super().setUp()

        self.users = {u.name: u.id for u in User.select()}

    def test_index(self):
        self._login("bob", "B0b")
        rv = self.client.get("/user", follow_redirects=True)
        self.assertIn("There's nothing much to see", rv.data)
        self.assertNotIn("Users", rv.data)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.get("/user")
        self.assertIn("Users", rv.data)

    def test_details(self):
        self._login("alice", "Alic3")
        rv = self.client.get("/user/string", follow_redirects=True)
        self.assertIn("badly formed", rv.data)
        rv = self.client.get("/user/" + str(uuid.uuid4()), follow_redirects=True)
        self.assertIn("No such user", rv.data)
        rv = self.client.get("/user/" + str(self.users["bob"]))
        self.assertIn("bob", rv.data)
        self._logout()

        ClientPrefs.create(user=User[self.users["bob"]], client_name="tests")

        self._login("bob", "B0b")
        rv = self.client.get("/user/" + str(self.users["alice"]), follow_redirects=True)
        self.assertIn("There's nothing much to see", rv.data)
        self.assertNotIn("<h2>bob</h2>", rv.data)
        rv = self.client.get("/user/me")
        self.assertIn('<h2 class="mt-4 pb-2 border-bottom">bob</h2>', rv.data)
        self.assertIn("tests", rv.data)

    def test_update_client_prefs(self):
        self._login("alice", "Alic3")
        rv = self.client.post("/user/me")
        self.assertIn("updated", rv.data)  # does nothing, says it's updated anyway
        # error cases, silently ignored
        self.client.post("/user/me", data={"garbage": "trash"})
        self.client.post("/user/me", data={"a_b_c_d_e_f": "g_h_i_j_k"})
        self.client.post("/user/me", data={"_l": "m"})
        self.client.post("/user/me", data={"n_": "o"})
        self.client.post("/user/me", data={"inexisting_client": "setting"})

        ClientPrefs.create(user=User[self.users["alice"]], client_name="tests")

        rv = self.client.post(
            "/user/me", data={"tests_format": "mp3", "tests_bitrate": 128}
        )
        self.assertIn("updated", rv.data)
        prefs = ClientPrefs[User[self.users["alice"]], "tests"]
        self.assertEqual(prefs.format, "mp3")
        self.assertEqual(prefs.bitrate, 128)

        # a garbage bitrate is reported, not a 500
        rv = self.client.post(
            "/user/me", data={"tests_format": "mp3", "tests_bitrate": "loud"}
        )
        self.assertEqual(rv.status_code, 200)
        self.assertIn("Invalid bitrate", rv.data)
        self.assertEqual(ClientPrefs[User[self.users["alice"]], "tests"].bitrate, 128)

        # an unchecked checkbox is either absent or explicitly negative
        self.client.post("/user/me", data={"tests_delete": "off"})
        self.assertEqual(ClientPrefs.select().count(), 1)

        self.client.post("/user/me", data={"tests_delete": 1})
        self.assertEqual(ClientPrefs.select().count(), 0)

    def test_change_username_get(self):
        self._login("bob", "B0b")
        rv = self.client.get("/user/whatever/changeusername", follow_redirects=True)
        self.assertIn("There's nothing much to see", rv.data)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.get("/user/whatever/changeusername", follow_redirects=True)
        self.assertIn("badly formed", rv.data)
        rv = self.client.get(
            f"/user/{uuid.uuid4()}/changeusername", follow_redirects=True
        )
        self.assertIn("No such user", rv.data)
        self.client.get("/user/{}/changeusername".format(self.users["bob"]))

    def test_change_username_post(self):
        self._login("alice", "Alic3")
        rv = self.client.post("/user/whatever/changeusername", follow_redirects=True)
        self.assertIn("badly formed", rv.data)
        rv = self.client.post(
            f"/user/{uuid.uuid4()}/changeusername", follow_redirects=True
        )
        self.assertIn("No such user", rv.data)

        path = "/user/{}/changeusername".format(self.users["bob"])
        rv = self.client.post(path, follow_redirects=True)
        self.assertIn("required", rv.data)
        rv = self.client.post(path, data={"user": "bob"}, follow_redirects=True)
        self.assertIn("No changes", rv.data)
        rv = self.client.post(
            path, data={"user": "b0b", "admin": 1}, follow_redirects=True
        )
        self.assertIn("updated", rv.data)
        self.assertIn("b0b", rv.data)
        bob = User[self.users["bob"]]
        self.assertEqual(bob.name, "b0b")
        self.assertTrue(bob.admin)
        rv = self.client.post(path, data={"user": "alice"}, follow_redirects=True)
        self.assertEqual(User[self.users["bob"]].name, "b0b")

        # an explicit negative doesn't grant admin
        rv = self.client.post(
            path, data={"user": "b0b", "admin": "false"}, follow_redirects=True
        )
        self.assertFalse(User[self.users["bob"]].admin)
        # ... and neither does omitting the checkbox
        self.client.post(path, data={"user": "b0b", "admin": 1}, follow_redirects=True)
        self.assertTrue(User[self.users["bob"]].admin)
        self.client.post(path, data={"user": "b0b"}, follow_redirects=True)
        self.assertFalse(User[self.users["bob"]].admin)

    def test_change_mail_get(self):
        self._login("alice", "Alic3")
        rv = self.client.get("/user/me/changemail")
        self.assertIn("eMail", rv.data)

    def test_change_mail_post(self):
        self._login("alice", "Alic3")
        path = "/user/me/changemail"

        self.client.post(path, data={"mail": "  alice@example.com  "})
        self.assertEqual(User[self.users["alice"]].mail, "alice@example.com")

        # an invalid address is rejected and changes nothing
        rv = self.client.post(path, data={"mail": "lolnope"})
        self.assertIn("Invalid email address", rv.data)
        self.assertEqual(User[self.users["alice"]].mail, "alice@example.com")

        # an empty address clears it
        self.client.post(path, data={"mail": ""})
        self.assertIsNone(User[self.users["alice"]].mail)

        # ... and so does an absent one
        self.client.post(path, data={"mail": "alice@example.com"})
        self.client.post(path)
        self.assertIsNone(User[self.users["alice"]].mail)

    def test_change_password_get(self):
        self._login("alice", "Alic3")
        rv = self.client.get("/user/me/changepass")
        self.assertIn("Current password", rv.data)
        rv = self.client.get("/user/{}/changepass".format(self.users["bob"]))
        self.assertNotIn("Current password", rv.data)

    def test_change_password_post(self):
        self._login("alice", "Alic3")
        path = "/user/me/changepass"
        rv = self.client.post(path)
        self.assertIn("required", rv.data)
        rv = self.client.post(path, data={"current": "alice"})
        self.assertIn("required", rv.data)
        rv = self.client.post(path, data={"new": "alice"})
        self.assertIn("required", rv.data)
        rv = self.client.post(path, data={"current": "alice", "new": "alice"})
        self.assertIn("password and its confirmation don", rv.data)
        rv = self.client.post(
            path, data={"current": "alice", "new": "alice", "confirm": "alice"}
        )
        self.assertIn("Wrong password", rv.data)
        self._logout()
        rv = self._login("alice", "Alic3")
        self.assertIn("Logged in", rv.data)
        rv = self.client.post(
            path,
            data={"current": "Alic3", "new": "alice", "confirm": "alice"},
            follow_redirects=True,
        )
        self.assertIn("changed", rv.data)
        self._logout()
        rv = self._login("alice", "alice")
        self.assertIn("Logged in", rv.data)

        path = "/user/{}/changepass".format(self.users["bob"])
        rv = self.client.post(path)
        self.assertIn("required", rv.data)
        rv = self.client.post(path, data={"new": "alice"})
        self.assertIn("password and its confirmation don", rv.data)
        rv = self.client.post(
            path, data={"new": "alice", "confirm": "alice"}, follow_redirects=True
        )
        self.assertIn("changed", rv.data)
        self._logout()
        rv = self._login("bob", "alice")
        self.assertIn("Logged in", rv.data)

    def test_add_get(self):
        self._login("bob", "B0b")
        rv = self.client.get("/user/add", follow_redirects=True)
        self.assertIn("There's nothing much to see", rv.data)
        self.assertNotIn("Add User", rv.data)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.get("/user/add")
        self.assertIn("Add User", rv.data)

    def test_add_post(self):
        self._login("alice", "Alic3")
        rv = self.client.post("/user/add")
        self.assertIn("required", rv.data)
        rv = self.client.post("/user/add", data={"user": "user"})
        self.assertIn("Please provide a password", rv.data)
        rv = self.client.post("/user/add", data={"passwd": "passwd"})
        self.assertIn("required", rv.data)
        rv = self.client.post("/user/add", data={"user": "name", "passwd": "passwd"})
        self.assertIn("passwords don", rv.data)
        rv = self.client.post(
            "/user/add",
            data={"user": "alice", "passwd": "passwd", "passwd_confirm": "passwd"},
        )
        self.assertIn("User 'alice' exists", html.unescape(rv.data))
        self.assertEqual(User.select().count(), 2)

        rv = self.client.post(
            "/user/add",
            data={
                "user": "user",
                "passwd": "passwd",
                "passwd_confirm": "passwd",
                "admin": 1,
            },
            follow_redirects=True,
        )
        self.assertIn("added", rv.data)
        self.assertEqual(User.select().count(), 3)
        self.assertIsNone(User.get(name="user").mail)
        self._logout()
        rv = self._login("user", "passwd")
        self.assertIn("Logged in", rv.data)

    def test_add_post_mail(self):
        self._login("alice", "Alic3")
        data = {"user": "user", "passwd": "passwd", "passwd_confirm": "passwd"}

        rv = self.client.post("/user/add", data=dict(data, mail="lolnope"))
        self.assertIn("Invalid email address", rv.data)
        self.assertEqual(User.select().count(), 2)

        rv = self.client.post(
            "/user/add",
            data=dict(data, mail="  user@example.com  "),
            follow_redirects=True,
        )
        self.assertIn("added", rv.data)
        self.assertEqual(User.get(name="user").mail, "user@example.com")

    def test_delete(self):
        path = "/user/del/{}".format(self.users["bob"])

        self._login("bob", "B0b")
        rv = self.client.post(path, follow_redirects=True)
        self.assertIn("There's nothing much to see", rv.data)
        self.assertEqual(User.select().count(), 2)
        self._logout()

        self._login("alice", "Alic3")
        rv = self.client.post("/user/del/string", follow_redirects=True)
        self.assertIn("badly formed", rv.data)
        rv = self.client.post("/user/del/" + str(uuid.uuid4()), follow_redirects=True)
        self.assertIn("No such user", rv.data)
        rv = self.client.post(path, follow_redirects=True)
        self.assertIn("Deleted", rv.data)
        self.assertEqual(User.select().count(), 1)
        self._logout()
        rv = self._login("bob", "B0b")
        self.assertIn("Wrong username or password", rv.data)

    def test_lastfm_link(self):
        self._login("alice", "Alic3")
        rv = self.client.get("/user/me/lastfm/link", follow_redirects=True)
        self.assertIn("Missing LastFM auth token", rv.data)
        rv = self.client.get(
            "/user/me/lastfm/link",
            query_string={"token": "abcdef"},
            follow_redirects=True,
        )
        self.assertIn("No API key set", rv.data)

    def test_lastfm_unlink(self):
        self._login("alice", "Alic3")
        rv = self.client.post("/user/me/lastfm/unlink", follow_redirects=True)
        self.assertIn("Unlinked", rv.data)

    def test_listenbrainz_unlink(self):
        self._login("alice", "Alic3")
        rv = self.client.post("/user/me/listenbrainz/unlink", follow_redirects=True)
        self.assertIn("Unlinked", rv.data)

    def test_listenbrainz_link(self):
        self._login("alice", "Alic3")
        rv = self.client.post("/user/me/listenbrainz/link", follow_redirects=True)
        self.assertIn("Missing ListenBrainz auth token", rv.data)

        # Invalid token: ListenBrainz reports it, the error is flashed back
        with patch("supysonic.listenbrainz.requests.get") as get:
            resp = Mock(status_code=200)
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"valid": False, "message": "bad token"}
            get.return_value = resp
            rv = self.client.post(
                "/user/me/listenbrainz/link",
                data={"token": "abcdef"},
                follow_redirects=True,
            )
            self.assertIn("Error: bad token", rv.data)

        # Valid token: account gets linked
        with patch("supysonic.listenbrainz.requests.get") as get:
            resp = Mock(status_code=200)
            resp.raise_for_status.return_value = None
            resp.json.return_value = {"valid": True}
            get.return_value = resp
            rv = self.client.post(
                "/user/me/listenbrainz/link",
                data={"token": "abcdef"},
                follow_redirects=True,
            )
            self.assertIn("Successfully linked", rv.data)


if __name__ == "__main__":
    unittest.main()

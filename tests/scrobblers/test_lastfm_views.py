# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
from unittest.mock import Mock, patch

from supysonic.db.models import User
from supysonic.scrobblers.lastfm.models import LastFmLink

from ..frontend.frontendtestbase import FrontendTestBase

LINK = "/scrobbler/lastfm/me/link"
UNLINK = "/scrobbler/lastfm/me/unlink"


def _response(json_data):
    r = Mock(status_code=200)
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


class LastFmViewsTestCase(FrontendTestBase):
    __sections__ = {"lastfm": {"api_key": "key", "secret": "secret"}}

    def setUp(self):
        super().setUp()

        self.alice = User.get(name="alice")
        self._login("alice", "Alic3")

    def test_link_requires_a_token(self):
        # Last.fm sends the token as a query param of its callback
        rv = self.client.get(LINK, follow_redirects=True)

        self.assertIn("Missing LastFM auth token", rv.data)
        self.assertEqual(LastFmLink.select().count(), 0)

    def test_link_reports_a_refusal(self):
        with patch("supysonic.scrobblers.lastfm.requests.get") as get:
            get.return_value = _response({"error": 4, "message": "Unauthorized"})
            rv = self.client.get(
                LINK, query_string={"token": "abcdef"}, follow_redirects=True
            )

        self.assertIn("Error 4: Unauthorized", rv.data)
        self.assertEqual(LastFmLink.select().count(), 0)

    def test_link(self):
        with patch("supysonic.scrobblers.lastfm.requests.get") as get:
            get.return_value = _response({"session": {"key": "a" * 32}})
            rv = self.client.get(
                LINK, query_string={"token": "abcdef"}, follow_redirects=True
            )

        self.assertIn("Successfully linked LastFM account", rv.data)
        self.assertEqual(
            LastFmLink.get(LastFmLink.user == self.alice).session_key, "a" * 32
        )

    def test_unlink(self):
        LastFmLink.create(user=self.alice, session_key="0" * 32, session_valid=False)

        rv = self.client.post(UNLINK, follow_redirects=True)

        self.assertIn("Unlinked LastFM account", rv.data)
        self.assertEqual(LastFmLink.select().count(), 0)

    def test_link_is_admin_only_for_others(self):
        # 'me' aside, acting on another user's account is reserved to admins
        self._logout()
        self._login("bob", "B0b")
        rv = self.client.post(
            f"/scrobbler/lastfm/{self.alice.id}/unlink", follow_redirects=True
        )

        self.assertIn("There's nothing much to see", rv.data)

    def test_profile_fragment(self):
        rv = self.client.get("/user/me")
        self.assertIn("LastFM status", rv.data)
        self.assertIn("Unlinked", rv.data)

        LastFmLink.create(user=self.alice, session_key="0" * 32, session_valid=True)
        rv = self.client.get("/user/me")
        self.assertIn('placeholder="Linked"', rv.data)

        LastFmLink.update(session_valid=False).execute()
        rv = self.client.get("/user/me")
        self.assertIn('placeholder="Invalid session"', rv.data)


class UnconfiguredLastFmViewsTestCase(FrontendTestBase):
    """Without an API key there's nothing to link to, and the page says so."""

    def setUp(self):
        super().setUp()
        self._login("alice", "Alic3")

    def test_profile_fragment(self):
        rv = self.client.get("/user/me")

        self.assertIn("LastFM status", rv.data)
        self.assertIn('placeholder="Unavailable"', rv.data)

    def test_link(self):
        rv = self.client.get(
            LINK, query_string={"token": "abcdef"}, follow_redirects=True
        )

        self.assertIn("No API key set", rv.data)
        self.assertEqual(LastFmLink.select().count(), 0)


if __name__ == "__main__":
    unittest.main()

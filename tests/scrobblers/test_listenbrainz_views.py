# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
from unittest.mock import Mock, patch

from supysonic.db.models import User
from supysonic.scrobblers.listenbrainz.models import ListenBrainzLink

from ..frontend.frontendtestbase import FrontendTestBase

LINK = "/scrobbler/listenbrainz/me/link"
UNLINK = "/scrobbler/listenbrainz/me/unlink"


def _response(json_data):
    r = Mock(status_code=200)
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


class ListenBrainzViewsTestCase(FrontendTestBase):
    def setUp(self):
        super().setUp()

        self.alice = User.get(name="alice")
        self._login("alice", "Alic3")

    def test_link_requires_a_token(self):
        rv = self.client.post(LINK, follow_redirects=True)

        self.assertIn("Missing ListenBrainz auth token", rv.data)
        self.assertEqual(ListenBrainzLink.select().count(), 0)

    def test_link_reports_a_refusal(self):
        with patch("supysonic.scrobblers.listenbrainz.requests.get") as get:
            get.return_value = _response({"valid": False, "message": "bad token"})
            rv = self.client.post(LINK, data={"token": "abcdef"}, follow_redirects=True)

        self.assertIn("Error: bad token", rv.data)
        self.assertEqual(ListenBrainzLink.select().count(), 0)

    def test_link(self):
        with patch("supysonic.scrobblers.listenbrainz.requests.get") as get:
            get.return_value = _response({"valid": True})
            rv = self.client.post(LINK, data={"token": "abcdef"}, follow_redirects=True)

        self.assertIn("Successfully linked ListenBrainz account", rv.data)
        self.assertEqual(
            ListenBrainzLink.get(ListenBrainzLink.user == self.alice).token, "abcdef"
        )

    def test_unlink(self):
        ListenBrainzLink.create(user=self.alice, token="0" * 36, token_valid=False)

        rv = self.client.post(UNLINK, follow_redirects=True)

        self.assertIn("Unlinked ListenBrainz account", rv.data)
        self.assertEqual(ListenBrainzLink.select().count(), 0)

    def test_link_is_admin_only_for_others(self):
        # 'me' aside, acting on another user's account is reserved to admins
        self._logout()
        self._login("bob", "B0b")
        rv = self.client.post(
            f"/scrobbler/listenbrainz/{self.alice.id}/unlink", follow_redirects=True
        )

        self.assertIn("There's nothing much to see", rv.data)

    def test_profile_fragment(self):
        rv = self.client.get("/user/me")
        self.assertIn("ListenBrainz status", rv.data)
        self.assertIn("Unlinked, insert auth token", rv.data)

        ListenBrainzLink.create(user=self.alice, token="0" * 36, token_valid=True)
        rv = self.client.get("/user/me")
        self.assertIn('placeholder="Linked"', rv.data)

        ListenBrainzLink.update(token_valid=False).execute()
        rv = self.client.get("/user/me")
        self.assertIn('placeholder="Invalid token"', rv.data)


class DisabledListenBrainzViewsTestCase(FrontendTestBase):
    """Leaving ListenBrainz out of the list is what turns it off.

    Unlike Last.fm it needs no credentials, so the only way not to have it is
    not to list it -- and then it has to leave no trace.
    """

    __sections__ = {"webapp": {"scrobblers": "lastfm"}}

    def setUp(self):
        super().setUp()
        self._login("alice", "Alic3")

    def test_no_profile_fragment(self):
        rv = self.client.get("/user/me")

        self.assertNotIn("ListenBrainz", rv.data)

    def test_no_routes(self):
        for rv in (
            self.client.post(LINK, data={"token": "abcdef"}),
            self.client.post(UNLINK),
        ):
            self.assertEqual(rv.status_code, 404)

        self.assertEqual(ListenBrainzLink.select().count(), 0)


if __name__ == "__main__":
    unittest.main()

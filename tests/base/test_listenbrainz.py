# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import json
import logging
import unittest
from unittest.mock import Mock, patch

import requests

from supysonic.db import User
from supysonic.listenbrainz import ListenBrainz

from ..testbase import TestBase


def _response(json_data, status_code=200):
    r = Mock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


def _http_error(status_code, message="oops"):
    err_response = Mock(status_code=status_code)
    err_response.json.return_value = {"error": message}
    r = _response({})
    r.raise_for_status.side_effect = requests.HTTPError(response=err_response)
    return r


def _track():
    track = Mock()
    track.album.artist.name = "Artist"
    track.title = "Title"
    track.album.name = "Album"
    track.number = 1
    track.duration = 123
    return track


class ListenBrainzTestCase(TestBase):
    def setUp(self):
        super().setUp()
        logging.getLogger("supysonic.listenbrainz").addHandler(logging.NullHandler())
        self.user = User.get(name="alice")

    def _listenbrainz(self, enabled=True):
        config = (
            {"api_url": "https://api.listenbrainz.org"}
            if enabled
            else {"api_url": None}
        )
        return ListenBrainz(config, self.user)

    def _request(self, lbz, *args, **kwargs):
        return lbz._ListenBrainz__api_request(*args, **kwargs)

    # __api_request enabled / token guards

    def test_disabled_api_request(self):
        rv = self._request(self._listenbrainz(enabled=False), False, "/route", "tok")
        self.assertIsNone(rv)

    @patch("supysonic.listenbrainz.requests.get")
    def test_api_request_no_token(self, get):
        rv = self._request(self._listenbrainz(), False, "/route", None)
        self.assertIsNone(rv)
        get.assert_not_called()

    # __api_request, read / write

    @patch("supysonic.listenbrainz.requests.get")
    def test_api_request_read(self, get):
        get.return_value = _response({"valid": True})
        rv = self._request(self._listenbrainz(), False, "/1/validate-token", "tok")
        self.assertEqual(rv, {"valid": True})
        get.assert_called_once()
        _, kwargs = get.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Token tok")

    @patch("supysonic.listenbrainz.requests.post")
    def test_api_request_write(self, post):
        post.return_value = _response({"status": "ok"})
        rv = self._request(
            self._listenbrainz(), True, "/1/submit-listens", "tok", listen_type="single"
        )
        self.assertEqual(rv, {"status": "ok"})
        post.assert_called_once()

    @patch("supysonic.listenbrainz.requests.get")
    def test_api_request_http_error_401_disables_status(self, get):
        get.return_value = _http_error(401, "Invalid token")
        rv = self._request(self._listenbrainz(), False, "/route", "tok")
        self.assertIsNone(rv)
        self.assertFalse(User.get(name="alice").listenbrainz_status)

    @patch("supysonic.listenbrainz.requests.get")
    def test_api_request_http_error_other_keeps_status(self, get):
        get.return_value = _http_error(500)
        rv = self._request(self._listenbrainz(), False, "/route", "tok")
        self.assertIsNone(rv)
        self.assertTrue(User.get(name="alice").listenbrainz_status)

    @patch("supysonic.listenbrainz.requests.get")
    def test_api_request_connection_error(self, get):
        get.side_effect = requests.exceptions.ConnectionError("boom")
        rv = self._request(self._listenbrainz(), False, "/route", "tok")
        self.assertIsNone(rv)

    # link_account

    def test_link_account_disabled(self):
        status, msg = self._listenbrainz(enabled=False).link_account("token")
        self.assertFalse(status)
        self.assertEqual(msg, "No ListenBrainz URL set")

    @patch("supysonic.listenbrainz.requests.get")
    def test_link_account_connection_error(self, get):
        get.side_effect = requests.exceptions.ConnectionError("boom")
        status, msg = self._listenbrainz().link_account("token")
        self.assertFalse(status)
        self.assertEqual(msg, "Error connecting to ListenBrainz")

    @patch("supysonic.listenbrainz.requests.get")
    def test_link_account_invalid(self, get):
        get.return_value = _response({"valid": False, "message": "bad token"})
        status, msg = self._listenbrainz().link_account("token")
        self.assertFalse(status)
        self.assertEqual(msg, "Error: bad token")

    @patch("supysonic.listenbrainz.requests.get")
    def test_link_account_success(self, get):
        get.return_value = _response({"valid": True, "message": "Token valid."})
        status, msg = self._listenbrainz().link_account("mytoken")
        self.assertTrue(status)
        self.assertEqual(msg, "OK")
        user = User.get(name="alice")
        self.assertEqual(user.listenbrainz_session, "mytoken")
        self.assertTrue(user.listenbrainz_status)

    def test_unlink_account(self):
        self.user.listenbrainz_session = "mytoken"
        self.user.listenbrainz_status = False
        self.user.save()
        self._listenbrainz().unlink_account()
        user = User.get(name="alice")
        self.assertIsNone(user.listenbrainz_session)
        self.assertTrue(user.listenbrainz_status)

    # now_playing / scrobble

    @patch("supysonic.listenbrainz.requests.post")
    def test_now_playing_scrobble_disabled(self, post):
        lbz = self._listenbrainz(enabled=False)
        lbz.now_playing(_track())
        lbz.scrobble(_track(), 1234)
        post.assert_not_called()

    @patch("supysonic.listenbrainz.requests.post")
    def test_now_playing(self, post):
        post.return_value = _response({"status": "ok"})
        self.user.listenbrainz_session = "sess"
        self._listenbrainz().now_playing(_track())
        _, kwargs = post.call_args
        data = json.loads(kwargs["data"])
        self.assertEqual(data["listen_type"], "playing_now")
        self.assertNotIn("listened_at", data["payload"][0])

    @patch("supysonic.listenbrainz.requests.post")
    def test_scrobble(self, post):
        post.return_value = _response({"status": "ok"})
        self.user.listenbrainz_session = "sess"
        self._listenbrainz().scrobble(_track(), 1234)
        _, kwargs = post.call_args
        data = json.loads(kwargs["data"])
        self.assertEqual(data["listen_type"], "single")
        self.assertEqual(data["payload"][0]["listened_at"], 1234)


if __name__ == "__main__":
    unittest.main()

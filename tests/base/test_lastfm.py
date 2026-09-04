# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import unittest
from unittest.mock import Mock, patch

import requests

from supysonic.db import User
from supysonic.lastfm import LastFm

from ..testbase import TestBase


def _response(json_data, status_code=200):
    r = Mock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status.return_value = None
    return r


def _track():
    track = Mock()
    track.album.artist.name = "Artist"
    track.title = "Title"
    track.album.name = "Album"
    track.number = 1
    track.duration = 123
    return track


class LastFmTestCase(TestBase):
    def setUp(self):
        super().setUp()
        logging.getLogger("supysonic.lastfm").addHandler(logging.NullHandler())
        self.user = User.get(name="alice")

    def _lastfm(self, enabled=True):
        config = (
            {"api_key": "key", "secret": "secret"}
            if enabled
            else {"api_key": None, "secret": None}
        )
        return LastFm(config)

    def _request(self, lfm, write, **kwargs):
        return lfm._LastFm__api_request(write, self.user, **kwargs)

    # __init__ / __api_request enabled flag

    def test_disabled_api_request(self):
        self.assertIsNone(self._request(self._lastfm(enabled=False), False))

    # __api_request, read path

    @patch("supysonic.lastfm.requests.get")
    def test_api_request_read(self, get):
        get.return_value = _response({"foo": "bar"})
        rv = self._request(self._lastfm(), False, method="dummy", accents="àéèùö")
        self.assertEqual(rv, {"foo": "bar"})
        get.assert_called_once()
        _, kwargs = get.call_args
        params = kwargs["params"]
        self.assertEqual(params["api_key"], "key")
        self.assertEqual(params["format"], "json")
        self.assertIn("api_sig", params)

    @patch("supysonic.lastfm.requests.post")
    @patch("supysonic.lastfm.requests.get")
    def test_api_request_connection_error(self, get, post):
        get.side_effect = requests.exceptions.ConnectionError("boom")
        self.assertIsNone(self._request(self._lastfm(), False, method="dummy"))
        post.assert_not_called()

    @patch("supysonic.lastfm.requests.get")
    def test_api_request_error_9_disables_status(self, get):
        get.return_value = _response({"error": 9, "message": "Invalid session key"})
        rv = self._request(self._lastfm(), False, method="dummy")
        self.assertEqual(rv["error"], 9)
        self.assertFalse(User.get(name="alice").lastfm_status)

    @patch("supysonic.lastfm.requests.get")
    def test_api_request_other_error_keeps_status(self, get):
        get.return_value = _response({"error": 6, "message": "Invalid parameters"})
        self._request(self._lastfm(), False, method="dummy")
        self.assertTrue(User.get(name="alice").lastfm_status)

    # __api_request, write path

    @patch("supysonic.lastfm.requests.post")
    def test_api_request_write_no_session(self, post):
        self.user.lastfm_session = None
        self.assertIsNone(self._request(self._lastfm(), True, method="dummy"))
        post.assert_not_called()

    @patch("supysonic.lastfm.requests.post")
    def test_api_request_write_bad_status(self, post):
        self.user.lastfm_session = "sess"
        self.user.lastfm_status = False
        self.assertIsNone(self._request(self._lastfm(), True, method="dummy"))
        post.assert_not_called()

    @patch("supysonic.lastfm.requests.post")
    def test_api_request_write(self, post):
        post.return_value = _response({"ok": 1})
        self.user.lastfm_session = "sess"
        self.user.lastfm_status = True
        self._request(self._lastfm(), True, method="dummy")
        post.assert_called_once()
        _, kwargs = post.call_args
        self.assertEqual(kwargs["data"]["sk"], "sess")

    # link_account

    def test_link_account_disabled(self):
        status, msg = self._lastfm(enabled=False).link_account(self.user, "token")
        self.assertFalse(status)
        self.assertEqual(msg, "No API key set")

    @patch("supysonic.lastfm.requests.get")
    def test_link_account_connection_error(self, get):
        get.side_effect = requests.exceptions.ConnectionError("boom")
        status, msg = self._lastfm().link_account(self.user, "token")
        self.assertFalse(status)
        self.assertEqual(msg, "Error connecting to LastFM")

    @patch("supysonic.lastfm.requests.get")
    def test_link_account_error(self, get):
        get.return_value = _response({"error": 4, "message": "Unauthorized"})
        status, msg = self._lastfm().link_account(self.user, "token")
        self.assertFalse(status)
        self.assertEqual(msg, "Error 4: Unauthorized")

    @patch("supysonic.lastfm.requests.get")
    def test_link_account_success(self, get):
        get.return_value = _response({"session": {"key": "abcdef"}})
        status, msg = self._lastfm().link_account(self.user, "token")
        self.assertTrue(status)
        self.assertEqual(msg, "OK")
        user = User.get(name="alice")
        self.assertEqual(user.lastfm_session, "abcdef")
        self.assertTrue(user.lastfm_status)

    def test_unlink_account(self):
        self.user.lastfm_session = "abcdef"
        self.user.lastfm_status = False
        self.user.save()
        self._lastfm().unlink_account(self.user)
        user = User.get(name="alice")
        self.assertIsNone(user.lastfm_session)
        self.assertTrue(user.lastfm_status)

    # now_playing / scrobble

    @patch("supysonic.lastfm.requests.post")
    def test_now_playing_scrobble_disabled(self, post):
        lastfm = self._lastfm(enabled=False)
        lastfm.now_playing(self.user, _track())
        lastfm.scrobble(self.user, _track(), 1234)
        post.assert_not_called()

    @patch("supysonic.lastfm.requests.post")
    def test_now_playing(self, post):
        post.return_value = _response({"ok": 1})
        self.user.lastfm_session = "sess"
        self.user.lastfm_status = True
        self._lastfm().now_playing(self.user, _track())
        _, kwargs = post.call_args
        self.assertEqual(kwargs["data"]["method"], "track.updateNowPlaying")

    @patch("supysonic.lastfm.requests.post")
    def test_scrobble(self, post):
        post.return_value = _response({"ok": 1})
        self.user.lastfm_session = "sess"
        self.user.lastfm_status = True
        self._lastfm().scrobble(self.user, _track(), 1234)
        _, kwargs = post.call_args
        self.assertEqual(kwargs["data"]["method"], "track.scrobble")
        self.assertEqual(kwargs["data"]["timestamp"], 1234)


if __name__ == "__main__":
    unittest.main()

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

from supysonic.config import Config
from supysonic.db.models import User
from supysonic.scrobblers.exceptions import (
    ScrobblerInvalidCredentialsError,
    ScrobblerUnavailableError,
)
from supysonic.scrobblers.lastfm import LastFm
from supysonic.scrobblers.lastfm.models import LastFmLink

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
        logging.getLogger("supysonic.scrobblers.lastfm").addHandler(
            logging.NullHandler()
        )
        self.user = User.get(name="alice")

    def _lastfm(self, configured=True):
        raw = {"lastfm": {"api_key": "key", "secret": "secret"}} if configured else {}
        return LastFm(Config(raw))

    def _link(self, session_key="sess", session_valid=True):
        return LastFmLink.create(
            user=self.user, session_key=session_key, session_valid=session_valid
        )

    def _request(self, lfm, write, link=None, **kwargs):
        return lfm._LastFm__api_request(write, link, **kwargs)

    # configured

    def test_configured(self):
        # Read when loading: saying no here is what keeps an unconfigured
        # Last.fm from being loaded at all
        self.assertTrue(self._lastfm().configured)
        self.assertFalse(self._lastfm(configured=False).configured)

        # Both halves of the credentials are needed
        half = LastFm(Config({"lastfm": {"api_key": "key"}}))
        self.assertFalse(half.configured)

    # __api_request, read path

    @patch("supysonic.scrobblers.lastfm.requests.get")
    def test_api_request_read(self, get):
        get.return_value = _response({"foo": "bar"})
        rv = self._request(self._lastfm(), False, method="dummy", accents="àéèùö")
        self.assertEqual(rv, {"foo": "bar"})
        get.assert_called_once()
        args, kwargs = get.call_args
        self.assertEqual(args[0], "https://ws.audioscrobbler.com/2.0/")
        params = kwargs["params"]
        self.assertEqual(params["api_key"], "key")
        self.assertEqual(params["format"], "json")
        self.assertIn("api_sig", params)

    @patch("supysonic.scrobblers.lastfm.requests.post")
    @patch("supysonic.scrobblers.lastfm.requests.get")
    def test_api_url_is_configurable(self, get, post):
        get.return_value = _response({"foo": "bar"})
        post.return_value = _response({"foo": "bar"})
        lastfm = LastFm(
            Config(
                {
                    "lastfm": {
                        "api_key": "key",
                        "secret": "secret",
                        "api_url": "http://localhost:8080/2.0/",
                    }
                }
            )
        )

        self._request(lastfm, False, method="dummy")
        self.assertEqual(get.call_args[0][0], "http://localhost:8080/2.0/")

        self._request(lastfm, True, self._link(), method="dummy")
        self.assertEqual(post.call_args[0][0], "http://localhost:8080/2.0/")

    @patch("supysonic.scrobblers.lastfm.requests.post")
    @patch("supysonic.scrobblers.lastfm.requests.get")
    def test_api_request_connection_error(self, get, post):
        get.side_effect = requests.exceptions.ConnectionError("boom")
        with self.assertRaises(ScrobblerUnavailableError):
            self._request(self._lastfm(), False, method="dummy")
        post.assert_not_called()

    # __api_request, write path

    @patch("supysonic.scrobblers.lastfm.requests.post")
    def test_api_request_write(self, post):
        post.return_value = _response({"ok": 1})
        self._request(self._lastfm(), True, self._link(), method="dummy")
        post.assert_called_once()
        _, kwargs = post.call_args
        self.assertEqual(kwargs["data"]["sk"], "sess")

    # is_linked / link

    def test_is_linked(self):
        lastfm = self._lastfm()
        self.assertIsNone(lastfm.link(self.user))
        self.assertFalse(lastfm.is_linked(self.user))

        link = self._link()
        self.assertEqual(lastfm.link(self.user).session_key, "sess")
        self.assertTrue(lastfm.is_linked(self.user))

        # A key the service rejected is as good as no link at all
        link.session_valid = False
        link.save()
        self.assertFalse(lastfm.is_linked(self.user))

    # link_account

    @patch("supysonic.scrobblers.lastfm.requests.get")
    def test_link_account_connection_error(self, get):
        get.side_effect = requests.exceptions.ConnectionError("boom")
        with self.assertRaises(ScrobblerUnavailableError) as cm:
            self._lastfm().link_account(self.user, "token")
        self.assertEqual(str(cm.exception), "Error connecting to LastFM")

    @patch("supysonic.scrobblers.lastfm.requests.get")
    def test_link_account_error(self, get):
        get.return_value = _response({"error": 4, "message": "Unauthorized"})
        with self.assertRaises(ScrobblerInvalidCredentialsError) as cm:
            self._lastfm().link_account(self.user, "token")
        self.assertEqual(str(cm.exception), "Error 4: Unauthorized")
        self.assertIsNone(self._lastfm().link(self.user))

    @patch("supysonic.scrobblers.lastfm.requests.get")
    def test_link_account_success(self, get):
        get.return_value = _response({"session": {"key": "abcdef"}})
        self._lastfm().link_account(self.user, "token")

        link = LastFmLink.get(LastFmLink.user == self.user)
        self.assertEqual(link.session_key, "abcdef")
        self.assertTrue(link.session_valid)

    @patch("supysonic.scrobblers.lastfm.requests.get")
    def test_link_account_again(self, get):
        # Re-linking replaces the stored key, and clears a rejection
        self._link("old", session_valid=False)
        get.return_value = _response({"session": {"key": "abcdef"}})
        self._lastfm().link_account(self.user, "token")

        (link,) = LastFmLink.select()
        self.assertEqual(link.session_key, "abcdef")
        self.assertTrue(link.session_valid)

    def test_unlink_account(self):
        self._link()
        self._lastfm().unlink_account(self.user)

        # The row only exists while linked
        self.assertEqual(LastFmLink.select().count(), 0)

    def test_unlink_account_not_linked(self):
        self._lastfm().unlink_account(self.user)
        self.assertEqual(LastFmLink.select().count(), 0)

    # now_playing / scrobble

    @patch("supysonic.scrobblers.lastfm.requests.post")
    def test_now_playing_scrobble_not_linked(self, post):
        lastfm = self._lastfm()
        lastfm.now_playing(self.user, _track(), "client")
        lastfm.scrobble(self.user, _track(), 1234, "client")
        post.assert_not_called()

    @patch("supysonic.scrobblers.lastfm.requests.post")
    def test_now_playing_scrobble_invalid_session(self, post):
        self._link(session_valid=False)
        lastfm = self._lastfm()
        lastfm.now_playing(self.user, _track(), "client")
        lastfm.scrobble(self.user, _track(), 1234, "client")
        post.assert_not_called()

    @patch("supysonic.scrobblers.lastfm.requests.post")
    def test_now_playing(self, post):
        post.return_value = _response({"ok": 1})
        self._link()
        self._lastfm().now_playing(self.user, _track(), "client")
        _, kwargs = post.call_args
        self.assertEqual(kwargs["data"]["method"], "track.updateNowPlaying")

    @patch("supysonic.scrobblers.lastfm.requests.post")
    def test_scrobble(self, post):
        post.return_value = _response({"ok": 1})
        self._link()
        self._lastfm().scrobble(self.user, _track(), 1234, "client")
        _, kwargs = post.call_args
        self.assertEqual(kwargs["data"]["method"], "track.scrobble")
        self.assertEqual(kwargs["data"]["timestamp"], 1234)

    @patch("supysonic.scrobblers.lastfm.requests.post")
    def test_scrobble_connection_error(self, post):
        # Reporting playback is fire-and-forget, a service that's down is not
        # the user's problem and doesn't invalidate their session
        post.side_effect = requests.exceptions.ConnectionError("boom")
        self._link()
        self._lastfm().scrobble(self.user, _track(), 1234, "client")

        self.assertTrue(LastFmLink.get(LastFmLink.user == self.user).session_valid)

    @patch("supysonic.scrobblers.lastfm.requests.post")
    def test_scrobble_error_9_invalidates_session(self, post):
        post.return_value = _response({"error": 9, "message": "Invalid session key"})
        self._link()
        self._lastfm().scrobble(self.user, _track(), 1234, "client")

        self.assertFalse(LastFmLink.get(LastFmLink.user == self.user).session_valid)

    @patch("supysonic.scrobblers.lastfm.requests.post")
    def test_scrobble_other_error_keeps_session(self, post):
        post.return_value = _response({"error": 6, "message": "Invalid parameters"})
        self._link()
        self._lastfm().scrobble(self.user, _track(), 1234, "client")

        self.assertTrue(LastFmLink.get(LastFmLink.user == self.user).session_valid)


if __name__ == "__main__":
    unittest.main()

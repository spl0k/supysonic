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

from supysonic import NAME, VERSION
from supysonic.config import Config
from supysonic.db.models import User
from supysonic.scrobblers.exceptions import (
    ScrobblerInvalidCredentialsError,
    ScrobblerUnavailableError,
)
from supysonic.scrobblers.listenbrainz import ListenBrainz
from supysonic.scrobblers.listenbrainz.models import ListenBrainzLink

from ..testbase import TestBase

CLIENT = "testclient"


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
        logging.getLogger("supysonic.scrobblers.listenbrainz").addHandler(
            logging.NullHandler()
        )
        self.user = User.get(name="alice")

    def _listenbrainz(self, api_url=None):
        raw = {"listenbrainz": {"api_url": api_url}} if api_url else {}
        return ListenBrainz(Config(raw))

    def _link(self, token="tok", token_valid=True):
        return ListenBrainzLink.create(
            user=self.user, token=token, token_valid=token_valid
        )

    def _request(self, lbz, write, route, token, **kwargs):
        return lbz._ListenBrainz__api_request(write, route, token, **kwargs)

    # configured

    def test_configured(self):
        # The API URL has a default, so ListenBrainz needs nothing to work
        self.assertTrue(self._listenbrainz().configured)

    # __api_request, read / write

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_api_request_read(self, get):
        get.return_value = _response({"valid": True})
        rv = self._request(self._listenbrainz(), False, "/1/validate-token", "tok")
        self.assertEqual(rv, {"valid": True})
        get.assert_called_once()
        args, kwargs = get.call_args
        self.assertEqual(args[0], "https://api.listenbrainz.org/1/validate-token")
        self.assertEqual(kwargs["headers"]["Authorization"], "Token tok")

    @patch("supysonic.scrobblers.listenbrainz.requests.post")
    def test_api_request_write(self, post):
        post.return_value = _response({"status": "ok"})
        rv = self._request(
            self._listenbrainz(), True, "/1/submit-listens", "tok", listen_type="single"
        )
        self.assertEqual(rv, {"status": "ok"})
        post.assert_called_once()

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_api_url_is_configurable(self, get):
        get.return_value = _response({"valid": True})
        lbz = self._listenbrainz(api_url="http://localhost:8080")
        self._request(lbz, False, "/1/validate-token", "tok")

        self.assertEqual(get.call_args[0][0], "http://localhost:8080/1/validate-token")

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_api_request_unauthorized(self, get):
        get.return_value = _http_error(401, "Invalid token")
        with self.assertRaises(ScrobblerInvalidCredentialsError) as cm:
            self._request(self._listenbrainz(), False, "/route", "tok")
        self.assertEqual(str(cm.exception), "Invalid token")

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_api_request_other_http_error(self, get):
        get.return_value = _http_error(500)
        with self.assertRaises(ScrobblerUnavailableError):
            self._request(self._listenbrainz(), False, "/route", "tok")

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_api_request_connection_error(self, get):
        get.side_effect = requests.exceptions.ConnectionError("boom")
        with self.assertRaises(ScrobblerUnavailableError) as cm:
            self._request(self._listenbrainz(), False, "/route", "tok")
        self.assertEqual(str(cm.exception), "Error connecting to ListenBrainz")

    # is_linked / link

    def test_is_linked(self):
        lbz = self._listenbrainz()
        self.assertIsNone(lbz.link(self.user))
        self.assertFalse(lbz.is_linked(self.user))

        link = self._link()
        self.assertEqual(lbz.link(self.user).token, "tok")
        self.assertTrue(lbz.is_linked(self.user))

        # A token the service rejected is as good as no link at all
        link.token_valid = False
        link.save()
        self.assertFalse(lbz.is_linked(self.user))

    # link_account

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_link_account_connection_error(self, get):
        get.side_effect = requests.exceptions.ConnectionError("boom")
        with self.assertRaises(ScrobblerUnavailableError) as cm:
            self._listenbrainz().link_account(self.user, "token")
        self.assertEqual(str(cm.exception), "Error connecting to ListenBrainz")

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_link_account_invalid(self, get):
        get.return_value = _response({"valid": False, "message": "bad token"})
        with self.assertRaises(ScrobblerInvalidCredentialsError) as cm:
            self._listenbrainz().link_account(self.user, "token")
        self.assertEqual(str(cm.exception), "Error: bad token")
        self.assertEqual(ListenBrainzLink.select().count(), 0)

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_link_account_success(self, get):
        get.return_value = _response({"valid": True, "message": "Token valid."})
        self._listenbrainz().link_account(self.user, "mytoken")

        link = ListenBrainzLink.get(ListenBrainzLink.user == self.user)
        self.assertEqual(link.token, "mytoken")
        self.assertTrue(link.token_valid)

    @patch("supysonic.scrobblers.listenbrainz.requests.get")
    def test_link_account_again(self, get):
        # Re-linking replaces the stored token, and clears a rejection
        self._link("old", token_valid=False)
        get.return_value = _response({"valid": True})
        self._listenbrainz().link_account(self.user, "mytoken")

        (link,) = ListenBrainzLink.select()
        self.assertEqual(link.token, "mytoken")
        self.assertTrue(link.token_valid)

    def test_unlink_account(self):
        self._link()
        self._listenbrainz().unlink_account(self.user)

        # The row only exists while linked
        self.assertEqual(ListenBrainzLink.select().count(), 0)

    def test_unlink_account_not_linked(self):
        self._listenbrainz().unlink_account(self.user)
        self.assertEqual(ListenBrainzLink.select().count(), 0)

    # now_playing / scrobble

    @patch("supysonic.scrobblers.listenbrainz.requests.post")
    def test_now_playing_scrobble_not_linked(self, post):
        lbz = self._listenbrainz()
        lbz.now_playing(self.user, _track(), CLIENT)
        lbz.scrobble(self.user, _track(), 1234, CLIENT)
        post.assert_not_called()

    @patch("supysonic.scrobblers.listenbrainz.requests.post")
    def test_now_playing_scrobble_invalid_token(self, post):
        self._link(token_valid=False)
        lbz = self._listenbrainz()
        lbz.now_playing(self.user, _track(), CLIENT)
        lbz.scrobble(self.user, _track(), 1234, CLIENT)
        post.assert_not_called()

    @patch("supysonic.scrobblers.listenbrainz.requests.post")
    def test_now_playing(self, post):
        post.return_value = _response({"status": "ok"})
        self._link()
        self._listenbrainz().now_playing(self.user, _track(), CLIENT)
        _, kwargs = post.call_args
        data = json.loads(kwargs["data"])
        self.assertEqual(data["listen_type"], "playing_now")
        self.assertNotIn("listened_at", data["payload"][0])

        info = data["payload"][0]["track_metadata"]["additional_info"]
        self.assertEqual(info["media_player"], CLIENT)
        self.assertEqual(info["submission_client"], NAME)
        self.assertEqual(info["submission_client_version"], VERSION)
        self.assertEqual(info["tracknumber"], "1")
        self.assertEqual(info["duration"], 123)

    @patch("supysonic.scrobblers.listenbrainz.requests.post")
    def test_scrobble(self, post):
        post.return_value = _response({"status": "ok"})
        self._link()
        self._listenbrainz().scrobble(self.user, _track(), 1234, CLIENT)
        _, kwargs = post.call_args
        data = json.loads(kwargs["data"])
        self.assertEqual(data["listen_type"], "single")
        self.assertEqual(data["payload"][0]["listened_at"], 1234)

    @patch("supysonic.scrobblers.listenbrainz.requests.post")
    def test_scrobble_connection_error(self, post):
        # Reporting playback is fire-and-forget, a service that's down is not
        # the user's problem and doesn't invalidate their token
        post.side_effect = requests.exceptions.ConnectionError("boom")
        self._link()
        self._listenbrainz().scrobble(self.user, _track(), 1234, CLIENT)

        self.assertTrue(
            ListenBrainzLink.get(ListenBrainzLink.user == self.user).token_valid
        )

    @patch("supysonic.scrobblers.listenbrainz.requests.post")
    def test_scrobble_unauthorized_invalidates_token(self, post):
        post.return_value = _http_error(401, "Invalid token")
        self._link()
        self._listenbrainz().scrobble(self.user, _track(), 1234, CLIENT)

        self.assertFalse(
            ListenBrainzLink.get(ListenBrainzLink.user == self.user).token_valid
        )

    @patch("supysonic.scrobblers.listenbrainz.requests.post")
    def test_scrobble_other_error_keeps_token(self, post):
        post.return_value = _http_error(500)
        self._link()
        self._listenbrainz().scrobble(self.user, _track(), 1234, CLIENT)

        self.assertTrue(
            ListenBrainzLink.get(ListenBrainzLink.user == self.user).token_valid
        )


if __name__ == "__main__":
    unittest.main()

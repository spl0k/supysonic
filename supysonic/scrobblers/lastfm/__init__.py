# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import hashlib
import logging

import requests

from ... import USER_AGENT
from ...db.proxy import db
from .. import Scrobbler
from ..exceptions import ScrobblerInvalidCredentialsError, ScrobblerUnavailableError
from .config import LastFmSection
from .models import LastFmLink
from .views import blueprint

logger = logging.getLogger(__name__)

# Last.fm's "Invalid session key - Please re-authenticate", the one error
# meaning the stored key is worthless rather than the call having failed
_INVALID_SESSION = (9, "9")


class LastFm(Scrobbler):
    name = "lastfm"
    blueprint = blueprint
    models = (LastFmLink,)

    def __init__(self, config):
        section = config.section(LastFmSection)

        self.__api_url = section.api_url
        self.__api_key = section.api_key
        self.__api_secret = section.secret

    @property
    def configured(self):
        return None not in (self.__api_url, self.__api_key, self.__api_secret)

    @property
    def api_key(self):
        """Read by the profile template, to build the authentication link."""

        return self.__api_key

    def link(self, user):
        """The user's link to their account, or None if there's none."""

        return LastFmLink.get_or_none(LastFmLink.user == user)

    def is_linked(self, user):
        return (
            LastFmLink.select()
            .where(LastFmLink.user == user, LastFmLink.session_valid == True)
            .exists()
        )

    def link_account(self, user, token):
        res = self.__api_request(False, None, method="auth.getSession", token=token)
        if "error" in res:
            raise ScrobblerInvalidCredentialsError(
                f"Error {res['error']}: {res['message']}"
            )

        with db.atomic():
            self.unlink_account(user)
            LastFmLink.create(
                user=user, session_key=res["session"]["key"], session_valid=True
            )

    def unlink_account(self, user):
        LastFmLink.delete().where(LastFmLink.user == user).execute()

    def now_playing(self, user, track, client):
        self.__submit(
            user,
            method="track.updateNowPlaying",
            artist=track.album.artist.name,
            track=track.title,
            album=track.album.name,
            trackNumber=track.number,
            duration=track.duration,
        )

    def scrobble(self, user, track, ts, client):
        self.__submit(
            user,
            method="track.scrobble",
            artist=track.album.artist.name,
            track=track.title,
            album=track.album.name,
            timestamp=ts,
            trackNumber=track.number,
            duration=track.duration,
        )

    def __submit(self, user, **kwargs):
        """Report playback, if there's anywhere to report it to.

        Fire-and-forget: a user who isn't linked, a service that's down or a
        rejected key are all logged at most, never raised.
        """

        link = self.link(user)
        if link is None or not link.session_valid:
            return

        try:
            res = self.__api_request(True, link, **kwargs)
        except ScrobblerUnavailableError:
            return

        if "error" in res:
            logger.warning("LastFM error %s: %s", res["error"], res["message"])
            if res["error"] in _INVALID_SESSION:
                link.session_valid = False
                link.save()

    def __api_request(self, write, link, **kwargs):
        """Call the API, signing the request as Last.fm expects.

        Returns the decoded response, which may well be reporting an error;
        only a failure to get one at all raises.
        """

        if write:
            kwargs["sk"] = link.session_key

        kwargs["api_key"] = self.__api_key

        sig_str = b""
        for k, v in sorted(kwargs.items()):
            k = k.encode("utf-8")
            v = v.encode("utf-8") if isinstance(v, str) else str(v).encode("utf-8")
            sig_str += k + v
        sig = hashlib.md5(sig_str + self.__api_secret.encode("utf-8")).hexdigest()

        kwargs["api_sig"] = sig
        kwargs["format"] = "json"

        headers = {"User-Agent": USER_AGENT}

        try:
            if write:
                r = requests.post(
                    self.__api_url, data=kwargs, headers=headers, timeout=5
                )
            else:
                r = requests.get(
                    self.__api_url, params=kwargs, headers=headers, timeout=5
                )

            return r.json()
        except requests.exceptions.RequestException as e:
            logger.warning("Error while connecting to LastFM: %s", e)
            raise ScrobblerUnavailableError("Error connecting to LastFM") from e


SCROBBLER = LastFm

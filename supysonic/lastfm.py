# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import hashlib
import logging

import requests

from . import USER_AGENT

logger = logging.getLogger(__name__)


class LastFm:
    def __init__(self, config):
        if config["api_key"] is not None and config["secret"] is not None:
            self.__api_key = config["api_key"]
            self.__api_secret = config["secret"].encode("utf-8")
            self.__enabled = True
        else:
            self.__enabled = False

    def link_account(self, user, token):
        if not self.__enabled:
            return False, "No API key set"

        res = self.__api_request(False, user, method="auth.getSession", token=token)
        if not res:
            return False, "Error connecting to LastFM"
        elif "error" in res:
            return False, f"Error {res['error']}: {res['message']}"
        else:
            user.lastfm_session = res["session"]["key"]
            user.lastfm_status = True
            user.save()
            return True, "OK"

    def unlink_account(self, user):
        user.lastfm_session = None
        user.lastfm_status = True
        user.save()

    def now_playing(self, user, track):
        if not self.__enabled:
            return

        self.__api_request(
            True,
            user,
            method="track.updateNowPlaying",
            artist=track.album.artist.name,
            track=track.title,
            album=track.album.name,
            trackNumber=track.number,
            duration=track.duration,
        )

    def scrobble(self, user, track, ts):
        if not self.__enabled:
            return

        self.__api_request(
            True,
            user,
            method="track.scrobble",
            artist=track.album.artist.name,
            track=track.title,
            album=track.album.name,
            timestamp=ts,
            trackNumber=track.number,
            duration=track.duration,
        )

    def __api_request(self, write, user, **kwargs):
        if not self.__enabled:
            return

        if write:
            if not user.lastfm_session or not user.lastfm_status:
                return
            kwargs["sk"] = user.lastfm_session

        kwargs["api_key"] = self.__api_key

        sig_str = b""
        for k, v in sorted(kwargs.items()):
            k = k.encode("utf-8")
            v = v.encode("utf-8") if isinstance(v, str) else str(v).encode("utf-8")
            sig_str += k + v
        sig = hashlib.md5(sig_str + self.__api_secret).hexdigest()

        kwargs["api_sig"] = sig
        kwargs["format"] = "json"

        headers = {"User-Agent": USER_AGENT}

        try:
            if write:
                r = requests.post(
                    "https://ws.audioscrobbler.com/2.0/",
                    data=kwargs,
                    headers=headers,
                    timeout=5,
                )
            else:
                r = requests.get(
                    "https://ws.audioscrobbler.com/2.0/",
                    params=kwargs,
                    headers=headers,
                    timeout=5,
                )
        except requests.exceptions.RequestException as e:
            logger.warning("Error while connecting to LastFM: " + str(e))
            return None

        json = r.json()
        if "error" in json:
            if json["error"] in (9, "9"):
                user.lastfm_status = False
                user.save()
            logger.warning("LastFM error %i: %s", json["error"], json["message"])

        return json

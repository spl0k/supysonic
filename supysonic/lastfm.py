# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import hashlib
import logging
import requests

logger = logging.getLogger(__name__)


class LastFm:
    def __init__(self, config, user):
        if config["api_key"] is not None and config["secret"] is not None:
            self.__api_key = config["api_key"]
            self.__api_secret = config["secret"].encode("utf-8")
            self.__enabled = True
        else:
            self.__enabled = False
        self.__user = user

    def link_account(self, token):
        if not self.__enabled:
            return False, "No API key set"

        res = self.__api_request(False, method="auth.getSession", token=token)
        if not res:
            return False, "Error connecting to LastFM"
        elif "error" in res:
            return False, f"Error {res['error']}: {res['message']}"
        else:
            self.__user.lastfm_session = res["session"]["key"]
            self.__user.lastfm_status = True
            self.__user.save()
            return True, "OK"

    def unlink_account(self):
        self.__user.lastfm_session = None
        self.__user.lastfm_status = True
        self.__user.save()

    def now_playing(self, track):
        if not self.__enabled:
            return

        self.__api_request(
            True,
            method="track.updateNowPlaying",
            artist=track.album.artist.name,
            track=track.title,
            album=track.album.name,
            trackNumber=track.number,
            duration=track.duration,
        )

    def scrobble(self, track, ts):
        if not self.__enabled:
            return

        self.__api_request(
            True,
            method="track.scrobble",
            artist=track.album.artist.name,
            track=track.title,
            album=track.album.name,
            timestamp=ts,
            trackNumber=track.number,
            duration=track.duration,
        )

    def __api_request(self, write, **kwargs):
        if not self.__enabled:
            return

        if write:
            if not self.__user.lastfm_session or not self.__user.lastfm_status:
                return
            kwargs["sk"] = self.__user.lastfm_session

        kwargs["api_key"] = self.__api_key

        sig_str = b""
        for k, v in sorted(kwargs.items()):
            k = k.encode("utf-8")
            v = v.encode("utf-8") if isinstance(v, str) else str(v).encode("utf-8")
            sig_str += k + v
        sig = hashlib.md5(sig_str + self.__api_secret).hexdigest()

        kwargs["api_sig"] = sig
        kwargs["format"] = "json"

        try:
            if write:
                r = requests.post(
                    "https://ws.audioscrobbler.com/2.0/", data=kwargs, timeout=5
                )
            else:
                r = requests.get(
                    "https://ws.audioscrobbler.com/2.0/", params=kwargs, timeout=5
                )
        except requests.exceptions.RequestException as e:
            logger.warning("Error while connecting to LastFM: " + str(e))
            return None

        json = r.json()
        if "error" in json:
            if json["error"] in (9, "9"):
                self.__user.lastfm_status = False
                self.__user.save()
            logger.warning("LastFM error %i: %s", json["error"], json["message"])

        return json

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
# Copyright (C) 2024 Iván Ávalos
#
# Distributed under terms of the GNU AGPLv3 license.

import json
import logging
from urllib.parse import urljoin

import requests

from . import NAME, USER_AGENT, VERSION

logger = logging.getLogger(__name__)


class ListenBrainz:
    def __init__(self, config, user):
        if config["api_url"] is not None:
            self.__api_url = config["api_url"]
            self.__enabled = True
        else:
            self.__enabled = False
        self.__user = user

    def link_account(self, token):
        if not self.__enabled:
            return False, "No ListenBrainz URL set"

        res = self.__api_request(False, "/1/validate-token", token)
        if not res:
            return False, "Error connecting to ListenBrainz"
        else:
            if "valid" in res and res["valid"]:
                self.__user.listenbrainz_session = token
                self.__user.listenbrainz_status = True
                self.__user.save()
                return True, "OK"
            else:
                return False, f"Error: {res['message']}"

    def unlink_account(self):
        self.__user.listenbrainz_session = None
        self.__user.listenbrainz_status = True
        self.__user.save()

    def now_playing(self, track, client):
        self.__submit_listen("playing_now", track, None, client)

    def scrobble(self, track, ts, client):
        self.__submit_listen("single", track, ts, client)

    def __submit_listen(self, type, track, ts, client):
        if not self.__enabled:
            return

        listen = {"track_metadata": self.__track_metadata(track, client)}
        if ts is not None:
            listen["listened_at"] = ts

        self.__api_request(
            True,
            "/1/submit-listens",
            self.__user.listenbrainz_session,
            listen_type=type,
            payload=[listen],
        )

    def __track_metadata(self, track, client):
        return {
            "artist_name": track.album.artist.name,
            "track_name": track.title,
            "release_name": track.album.name,
            "additional_info": {
                "media_player": client,
                "submission_client": NAME,
                "submission_client_version": VERSION,
                "tracknumber": str(track.number),
                "duration": track.duration,
            },
        }

    def __api_request(self, write, route, token, **kwargs):
        if not self.__enabled or not token:
            return

        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Authorization": f"Token {token}",
        }

        try:
            if write:
                r = requests.post(
                    urljoin(self.__api_url, route),
                    headers=headers,
                    data=json.dumps(kwargs),
                    timeout=5,
                )
            else:
                r = requests.get(
                    urljoin(self.__api_url, route),
                    headers=headers,
                    data=json.dumps(kwargs),
                    timeout=5,
                )

            r.raise_for_status()
        except requests.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:  # Unauthorized
                self.__user.listenbrainz_status = False
                self.__user.save()
            message = e.response.json().get("error", "")
            logger.warning("ListenBrainz error %i: %s", status_code, message)
            return None
        except requests.exceptions.RequestException as e:
            logger.warning("Error while connecting to ListenBrainz: " + str(e))
            return None

        return r.json()

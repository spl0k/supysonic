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

from ... import NAME, USER_AGENT, VERSION
from ...db.proxy import db
from .. import Scrobbler
from ..exceptions import ScrobblerInvalidCredentialsError, ScrobblerUnavailableError
from .config import ListenBrainzSection
from .models import ListenBrainzLink
from .views import blueprint

logger = logging.getLogger(__name__)


class ListenBrainz(Scrobbler):
    name = "listenbrainz"
    blueprint = blueprint
    models = (ListenBrainzLink,)

    def __init__(self, config):
        section = config.section(ListenBrainzSection)

        self.__api_url = section.api_url

    @property
    def configured(self):
        return self.__api_url is not None

    def link(self, user):
        """The user's link to their account, or None if there's none."""

        return ListenBrainzLink.get_or_none(ListenBrainzLink.user == user)

    def is_linked(self, user):
        return (
            ListenBrainzLink.select()
            .where(ListenBrainzLink.user == user, ListenBrainzLink.token_valid == True)
            .exists()
        )

    def link_account(self, user, token):
        res = self.__api_request(False, "/1/validate-token", token)
        if not res.get("valid"):
            raise ScrobblerInvalidCredentialsError(f"Error: {res.get('message')}")

        with db.atomic():
            self.unlink_account(user)
            ListenBrainzLink.create(user=user, token=token, token_valid=True)

    def unlink_account(self, user):
        ListenBrainzLink.delete().where(ListenBrainzLink.user == user).execute()

    def now_playing(self, user, track, client):
        self.__submit_listen(user, "playing_now", track, None, client)

    def scrobble(self, user, track, ts, client):
        self.__submit_listen(user, "single", track, ts, client)

    def __submit_listen(self, user, type, track, ts, client):
        """Report playback, if there's anywhere to report it to.

        Fire-and-forget: a user who isn't linked, a service that's down or a
        rejected token are all logged at most, never raised.
        """

        link = self.link(user)
        if link is None or not link.token_valid:
            return

        listen = {"track_metadata": self.__track_metadata(track, client)}
        if ts is not None:
            listen["listened_at"] = ts

        try:
            self.__api_request(
                True,
                "/1/submit-listens",
                link.token,
                listen_type=type,
                payload=[listen],
            )
        except ScrobblerInvalidCredentialsError:
            link.token_valid = False
            link.save()
        except ScrobblerUnavailableError:
            pass

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
        """Call the API, authenticating with ``token``.

        Returns the decoded response. A token the service refuses raises
        :class:`ScrobblerInvalidCredentialsError`, anything else going wrong
        raises :class:`ScrobblerUnavailableError`.
        """

        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Authorization": f"Token {token}",
        }
        url = urljoin(self.__api_url, route)
        data = json.dumps(kwargs)

        try:
            if write:
                r = requests.post(url, headers=headers, data=data, timeout=5)
            else:
                r = requests.get(url, headers=headers, data=data, timeout=5)

            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            status_code = e.response.status_code
            message = e.response.json().get("error", "")
            logger.warning("ListenBrainz error %s: %s", status_code, message)

            if status_code == 401:  # Unauthorized
                raise ScrobblerInvalidCredentialsError(message) from e
            raise ScrobblerUnavailableError(message) from e
        except requests.exceptions.RequestException as e:
            logger.warning("Error while connecting to ListenBrainz: %s", e)
            raise ScrobblerUnavailableError("Error connecting to ListenBrainz") from e


SCROBBLER = ListenBrainz

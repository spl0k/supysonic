# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.


import os.path
from contextlib import suppress

from flask import current_app
from werkzeug.local import LocalProxy

from ..cache import Cache
from ..db.connection import close_connection, open_connection
from ..db.exceptions import DatabaseNotInitializedError
from ..lastfm import LastFm
from ..listenbrainz import ListenBrainz
from ..secret import get_secret_key
from .base import SupysonicBaseAppLayer


# Request hooks, only registered on a non-testing app hence never covered
def _open_conn():  # pragma: nocover
    # Just to discard the return value, a truthy one would be used as response
    open_connection()


def _close_conn(exc):  # pragma: nocover
    # Tearing down a request of an app whose database has been released isn't
    # worth masking whatever exception is being handled here
    with suppress(DatabaseNotInitializedError):
        close_connection()


class SupysonicFlaskAppLayer(SupysonicBaseAppLayer):
    """Application layer for the web app.

    Contrary to the base layer, this one is never used as a context manager:
    the Flask app it binds the database for outlives any scope, so the database
    stays bound for the lifetime of the process.
    """

    def __init__(self, app):
        super().__init__(app.config)

        # Initialize Cache objects
        # Max size is MB in the config file but Cache expects bytes
        cache_path = app.config["WEBAPP"]["cache_dir"]
        max_size_cache = app.config["WEBAPP"]["cache_size"] * 1024**2
        max_size_transcodes = app.config["WEBAPP"]["transcode_cache_size"] * 1024**2
        self._cache = Cache(os.path.join(cache_path, "cache"), max_size_cache)
        self._transcode_cache = Cache(
            os.path.join(cache_path, "transcodes"), max_size_transcodes
        )

        self._lastfm = LastFm(app.config["LASTFM"])
        self._listenbrainz = ListenBrainz(app.config["LISTENBRAINZ"])

        # Read or create secret key
        app.secret_key = get_secret_key("cookies_secret")

        if not app.testing:  # pragma: nocover
            app.before_request(_open_conn)
            app.teardown_request(_close_conn)
            close_connection()

        app.extensions["supysonic"] = self

    cache = property(lambda self: self._cache)
    transcode_cache = property(lambda self: self._transcode_cache)
    lastfm = property(lambda self: self._lastfm)
    listenbrainz = property(lambda self: self._listenbrainz)

    @classmethod
    def register_on(cls, app):
        """Simple factory that reads better than just calling a constructor"""
        return cls(app)


def _get_flask_layer():
    return current_app.extensions["supysonic"]


app_layer = LocalProxy(_get_flask_layer)

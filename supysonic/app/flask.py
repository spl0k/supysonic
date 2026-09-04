# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.


import os.path

from flask import current_app
from werkzeug.local import LocalProxy

from ..cache import Cache
from ..lastfm import LastFm
from ..listenbrainz import ListenBrainz
from .base import SupysonicBaseAppLayer


class SupysonicFlaskAppLayer(SupysonicBaseAppLayer):
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

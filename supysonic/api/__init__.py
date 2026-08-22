# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import pkgutil
from functools import cache
from importlib import import_module

from ._exceptions import GenericError

API_VERSION = "1.12.0"

_UNSUPPORTED_METHODS = (
    "getVideos",
    "getAvatar",
    "getShares",
    "createShare",
    "updateShare",
    "deleteShare",
    "hls",
)


def _unsupported():
    return GenericError("Not supported by Supysonic")


@cache
def get_api_blueprint():
    from ._blueprint import api

    for name in sorted(m.name for m in pkgutil.iter_modules(__path__)):
        if not name.startswith("_"):
            import_module(f".{name}", __package__)

    for method in _UNSUPPORTED_METHODS:
        api.add_url_rule(
            f"/{method}", "unsupported", _unsupported, methods=["GET", "POST"]
        )
        api.add_url_rule(
            f"/{method}.view", "unsupported", _unsupported, methods=["GET", "POST"]
        )

    return api

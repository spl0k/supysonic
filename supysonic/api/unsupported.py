# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from . import api
from .exceptions import GenericError

methods = (
    "getVideos",
    "getAvatar",
    "getShares",
    "createShare",
    "updateShare",
    "deleteShare",
)


def unsupported():
    return GenericError("Not supported by Supysonic")


for m in methods:
    api.add_url_rule(
        "/{}".format(m), "unsupported", unsupported, methods=["GET", "POST"]
    )
    api.add_url_rule(
        "/{}.view".format(m), "unsupported", unsupported, methods=["GET", "POST"]
    )

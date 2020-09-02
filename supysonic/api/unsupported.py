# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from . import api
from .exceptions import GenericError

methods = (
    "getAvatar",
    "getShares",
    "createShare",
    "updateShare",
    "deleteShare",
)


def unsupported():
    return GenericError("Not supported by Supysonic"), 501


for m in methods:
    api.add_url_rule(
        "/{}.view".format(m), "unsupported", unsupported, methods=["GET", "POST"]
    )

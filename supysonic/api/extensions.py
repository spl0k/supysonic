#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2024 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from . import api_routing


@api_routing("/getOpenSubsonicExtensions")
def extensions():
    return request.formatter("openSubsonicExtensions", [])

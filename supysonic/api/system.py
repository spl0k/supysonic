#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from ._blueprint import api_routing


@api_routing("/ping")
def ping():
    return request.formatter.empty


@api_routing("/getLicense")
def license():
    return request.formatter("license", {"valid": True})

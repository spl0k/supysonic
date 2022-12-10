# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from base64 import b64encode, b64decode
from os import urandom

from supysonic.db import Meta


__key_cache = {}


def get_secret_key(keyname):
    if keyname in __key_cache:
        return __key_cache[keyname]

    try:
        key = b64decode(Meta[keyname].value)
    except Meta.DoesNotExist:
        key = urandom(128)
        Meta.create(key=keyname, value=b64encode(key).decode())

    __key_cache[keyname] = key
    return key

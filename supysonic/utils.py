# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from base64 import b64decode, b64encode
from functools import cache
from os import urandom

from .db import Meta, db


@cache
def get_secret_key(keyname):
    with db.atomic():
        m, created = Meta.get_or_create(key=keyname, defaults={"value": ""})
        if created:
            key = urandom(128)
            m.value = b64encode(key)
            m.save()
        else:
            key = b64decode(m.value)

    return key

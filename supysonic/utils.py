# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.
import uuid

from base64 import b64encode, b64decode
from os import urandom
from pony.orm import db_session, commit, ObjectNotFound

from supysonic.db import Folder, Meta


@db_session
def get_secret_key(keyname):
    # Commit both at enter and exit. The metadb/db split (from supysonic.db)
    # confuses Pony which can either error or hang when this method is called
    commit()
    try:
        key = b64decode(Meta[keyname].value)
    except ObjectNotFound:
        key = urandom(128)
        Meta(key=keyname, value=b64encode(key).decode())
    commit()
    return key

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from peewee import MySQLDatabase, fn

from .proxy import db


def random():
    if isinstance(db.obj, MySQLDatabase):
        return fn.rand()
    return fn.random()

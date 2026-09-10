# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from peewee import DatabaseProxy, Model as _Model

db = DatabaseProxy()


class Model(_Model):
    class Meta:
        database = db
        legacy_table_names = False

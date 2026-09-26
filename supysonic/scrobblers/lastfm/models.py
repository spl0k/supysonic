# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from peewee import BooleanField, FixedCharField, ForeignKeyField

from ...db.models import User
from ...db.proxy import Model


class LastFmLink(Model):
    """A user's link to their Last.fm account.

    The row only exists while the account is linked, so ``session_valid`` says
    one thing only: whether Last.fm still accepts the session key held here.
    """

    user = ForeignKeyField(User, primary_key=True, backref="+")
    session_key = FixedCharField(32)
    session_valid = BooleanField(default=True)

    class Meta:
        # Peewee would derive 'last_fm_link' from the class name
        table_name = "lastfm_link"

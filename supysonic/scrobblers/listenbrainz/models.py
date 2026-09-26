# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from peewee import BooleanField, FixedCharField, ForeignKeyField

from ...db.models import User
from ...db.proxy import Model


class ListenBrainzLink(Model):
    """A user's link to their ListenBrainz account.

    The row only exists while the account is linked, so ``token_valid`` says one
    thing only: whether ListenBrainz still accepts the token held here.
    """

    user = ForeignKeyField(User, primary_key=True, backref="+")
    token = FixedCharField(36)
    token_valid = BooleanField(default=True)

    class Meta:
        # Peewee would derive 'listen_brainz_link' from the class name
        table_name = "listenbrainz_link"

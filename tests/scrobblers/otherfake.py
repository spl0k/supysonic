# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""A second scrobbler, for the tests needing more than one loaded."""

from supysonic.scrobblers import make_blueprint

from .fakes import FakeScrobblerBase


class OtherScrobbler(FakeScrobblerBase):
    name = "other"
    blueprint = make_blueprint(name, __name__)


SCROBBLER = OtherScrobbler

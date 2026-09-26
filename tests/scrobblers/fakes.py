# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Scrobbler-shaped modules for the loading tests.

They stand in for an out-of-tree scrobbler, loaded through the dotted path form
of the ``scrobblers`` option, and for the ways a module can fail to be one.
"""

from supysonic.frontend._helpers import me_or_uuid
from supysonic.scrobblers import Scrobbler, make_blueprint


class FakeScrobblerBase(Scrobbler):
    """Everything a scrobbler has to implement, recording what it's told."""

    # Flipped by the tests checking a listed but unconfigured scrobbler is
    # skipped. Declared here so patching it on one subclass leaves the other
    # alone.
    configured = True

    def __init__(self, config):
        self.config = config
        self.scrobbled = []
        self.playing = []

    def link_account(self, user, token):
        pass

    def unlink_account(self, user):
        pass

    def is_linked(self, user):
        return False

    def now_playing(self, user, track, client):
        self.playing.append((user, track, client))

    def scrobble(self, user, track, ts, client):
        self.scrobbled.append((user, track, ts, client))


class FakeScrobbler(FakeScrobblerBase):
    name = "fake"
    blueprint = make_blueprint(name, __name__)


SCROBBLER = FakeScrobbler


@FakeScrobbler.blueprint.get("/<uid>/whoami")
@me_or_uuid
def whoami(uid, user):
    """Stands in for the link/unlink routes of a real scrobbler."""

    return user.name

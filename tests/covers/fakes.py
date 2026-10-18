# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Cover art provider modules for the loading and integration tests.

They stand in for an out-of-tree provider, loaded through the dotted path form
of the ``cover_art_providers`` option.
"""

from io import BytesIO

from PIL import Image

from supysonic.covers import Cover, CoverArtProvider


def png(size=32):
    """The raw contents of a ``size`` pixels wide square PNG image."""

    with BytesIO() as buf:
        Image.new("RGB", (size, size), "red").save(buf, "PNG")
        return buf.getvalue()


class FakeProviderBase(CoverArtProvider):
    """Everything a provider has to implement, recording what it's asked.

    What it answers is set by the tests, keyed by entity id: ``announces`` for
    the id :meth:`find_covers` gives, ``covers`` for what :meth:`get_cover`
    returns.
    """

    # Flipped by the tests checking a listed but unconfigured provider is
    # skipped. Declared here so patching it on one subclass leaves the other
    # alone.
    configured = True

    def __init__(self, config):
        self.config = config
        self.announces = {}
        self.covers = {}
        self.asked = []  # One list of entity ids per find_covers() call
        self.served = []  # The ids of the entities given to get_cover()

    def find_covers(self, entities):
        ids = [str(e.id) for e in entities]
        self.asked.append(ids)
        return {eid: self.announces[eid] for eid in ids if eid in self.announces}

    def get_cover(self, entity):
        self.served.append(str(entity.id))
        return self.covers.get(str(entity.id))


class FakeProvider(FakeProviderBase):
    name = "fake"


def cover(size=32):
    return Cover(data=png(size))


PROVIDER = FakeProvider

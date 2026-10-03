# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Lyrics provider modules for the loading and integration tests.

They stand in for an out-of-tree provider, loaded through the dotted path form
of the ``lyrics_providers`` option.
"""

from supysonic.lyrics import Lyrics, LyricsProvider


class FakeProviderBase(LyricsProvider):
    """Everything a provider has to implement, recording what it's asked."""

    # Flipped by the tests checking a listed but unconfigured provider is
    # skipped. Declared here so patching it on one subclass leaves the other
    # alone.
    configured = True

    answer = None

    def __init__(self, config):
        self.config = config
        self.asked = []

    def get_lyrics(self, artist, title):
        self.asked.append((artist, title))
        return self.answer


class FakeProvider(FakeProviderBase):
    name = "fake"
    answer = Lyrics("Fake artist", "Fake title", "Fake lyrics")


PROVIDER = FakeProvider

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""A second provider, for the tests needing more than one loaded.

It never finds anything, which is what lets the next one be asked.
"""

from .fakes import FakeProviderBase


class SilentProvider(FakeProviderBase):
    name = "silent"


PROVIDER = SilentProvider

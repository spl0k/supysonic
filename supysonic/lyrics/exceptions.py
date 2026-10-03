# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.


"""Errors raised about a lyrics provider."""


class LyricsProviderError(Exception):
    """Base class for lyrics provider related errors."""


class LyricsProviderImportError(LyricsProviderError):
    """A configured lyrics provider couldn't be imported and loaded."""

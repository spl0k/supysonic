# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.


class ScrobblerError(Exception):
    """Base class for scrobbler related errors."""


class ScrobblerUnavailableError(ScrobblerError):
    """The service couldn't be reached."""


class ScrobblerInvalidCredentialsError(ScrobblerError):
    """The service refused the credentials it was handed."""


class ScrobblerImportError(ScrobblerError):
    """A configured scrobbler couldn't be imported and loaded."""

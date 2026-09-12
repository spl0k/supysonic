# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.


class DatabaseError(Exception):
    pass


class DatabaseAlreadyInitializedError(DatabaseError):
    pass


class DatabaseNotInitializedError(DatabaseError):
    pass


class UnsupportedDatabaseError(DatabaseError):
    pass

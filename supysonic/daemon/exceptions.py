# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.


class DaemonUnavailableError(Exception):
    pass


class UnknownCommandError(Exception):
    def __init__(self, tag):
        super().__init__(f"Unknown command {tag!r}")
        self.tag = tag

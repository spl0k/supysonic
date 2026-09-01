# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.


from ..managers.folder import FolderManager
from ..managers.user import UserManager


class SupysonicBaseAppLayer:
    def __init__(self, config):
        self._config = config
        self._users = UserManager()
        self._folders = FolderManager(config)

    config = property(lambda self: self._config)
    users = property(lambda self: self._users)
    folders = property(lambda self: self._folders)

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import os.path

from ..daemon.exceptions import DaemonUnavailableError
from ..db import Album, Artist, Folder
from ..pathutils import is_subpath, subpath_expr

logger = logging.getLogger(__name__)


class FolderManager:
    def __init__(self, daemon=None):
        self.__daemon = daemon  # Allow none for tests

    def get(self, id):
        try:
            id = int(id)
        except ValueError:
            raise ValueError("Invalid folder id")

        return Folder[id]

    def add(self, name, path):
        try:
            Folder.get(name=name, root=True)
            raise ValueError(f"Folder '{name}' exists")
        except Folder.DoesNotExist:
            pass

        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            raise ValueError("The path doesn't exits or isn't a directory")

        try:
            Folder.get(path=path)
            raise ValueError("This path is already registered")
        except Folder.DoesNotExist:
            pass

        if any(
            is_subpath(path, p)
            for (p,) in Folder.select(Folder.path).where(Folder.root).tuples()
        ):
            raise ValueError("This path is already registered")
        if Folder.select().where(subpath_expr(Folder.path, path)).exists():
            raise ValueError("This path contains a folder that is already registered")

        folder = Folder.create(root=True, name=name, path=path)
        try:
            if self.__daemon is not None:
                self.__daemon.add_watched_folder(path)
        except DaemonUnavailableError:
            # The daemon is optional, but if one is running and merely
            # unreachable the folder stays unwatched until it restarts.
            logger.debug(
                "Couldn't connect to the daemon, folder '%s' won't be watched", name
            )

        return folder

    def delete(self, id):
        folder = self.get(id)
        if not folder.root:
            raise Folder.DoesNotExist(id)

        try:
            if self.__daemon is not None:
                self.__daemon.remove_watched_folder(folder.path)
        except DaemonUnavailableError:
            # Same as in add(): a running but unreachable daemon keeps watching
            # a folder that no longer exists until it restarts.
            logger.debug(
                "Couldn't connect to the daemon, folder '%s' stays watched", folder.name
            )

        folder.delete_hierarchy()
        Album.prune()
        Artist.prune()

    def delete_by_name(self, name):
        folder = Folder.get(name=name, root=True)
        self.delete(folder.id)

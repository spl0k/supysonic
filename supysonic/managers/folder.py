# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path

from ..daemon.client import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError
from ..db import Folder, Artist, Album


class FolderManager:
    @staticmethod
    def get(id):
        try:
            id = int(id)
        except ValueError:
            raise ValueError("Invalid folder id")

        return Folder[id]

    @staticmethod
    def add(name, path):
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
            path.startswith(p)
            for (p,) in Folder.select(Folder.path).where(Folder.root).tuples()
        ):
            raise ValueError("This path is already registered")
        if Folder.select().where(Folder.path.startswith(path)).exists():
            raise ValueError("This path contains a folder that is already registered")

        folder = Folder.create(root=True, name=name, path=path)
        try:
            DaemonClient().add_watched_folder(path)
        except DaemonUnavailableError:
            pass

        return folder

    @staticmethod
    def delete(id):
        folder = FolderManager.get(id)
        if not folder.root:
            raise Folder.DoesNotExist(id)

        try:
            DaemonClient().remove_watched_folder(folder.path)
        except DaemonUnavailableError:
            pass

        folder.delete_hierarchy()
        Album.prune()
        Artist.prune()

    @staticmethod
    def delete_by_name(name):
        folder = Folder.get(name=name, root=True)
        FolderManager.delete(folder.id)

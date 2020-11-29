# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2019 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path

from pony.orm import select
from pony.orm import ObjectNotFound

from ..daemon.client import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError
from ..db import Folder, Track, Artist, Album, User, RatingTrack, StarredTrack


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
        if Folder.get(name=name, root=True) is not None:
            raise ValueError("Folder '{}' exists".format(name))

        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isdir(path):
            raise ValueError("The path doesn't exits or isn't a directory")
        if Folder.get(path=path) is not None:
            raise ValueError("This path is already registered")
        if any(path.startswith(p) for p in select(f.path for f in Folder if f.root)):
            raise ValueError("This path is already registered")
        if Folder.exists(lambda f: f.path.startswith(path)):
            raise ValueError("This path contains a folder that is already registered")

        folder = Folder(root=True, name=name, path=path)
        try:
            DaemonClient().add_watched_folder(path)
        except DaemonUnavailableError:
            pass

        return folder

    @staticmethod
    def delete(id):
        folder = FolderManager.get(id)
        if not folder.root:
            raise ObjectNotFound(Folder)

        try:
            DaemonClient().remove_watched_folder(folder.path)
        except DaemonUnavailableError:
            pass

        for user in User.select(lambda u: u.last_play.root_folder == folder):
            user.last_play = None
        RatingTrack.select(lambda r: r.rated.root_folder == folder).delete(bulk=True)
        StarredTrack.select(lambda s: s.starred.root_folder == folder).delete(bulk=True)

        Track.select(lambda t: t.root_folder == folder).delete(bulk=True)
        Album.prune()
        Artist.prune()
        Folder.select(lambda f: not f.root and f.path.startswith(folder.path)).delete(
            bulk=True
        )

        folder.delete()

    @staticmethod
    def delete_by_name(name):
        folder = Folder.get(name=name, root=True)
        if not folder:
            raise ObjectNotFound(Folder)
        FolderManager.delete(folder.id)

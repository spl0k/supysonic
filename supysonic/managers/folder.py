# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import uuid

from pony.orm import select
from pony.orm import ObjectNotFound

from ..db import Folder, Track, Artist, Album
from ..py23 import strtype

class FolderManager:
    @staticmethod
    def get(uid):
        if isinstance(uid, strtype):
            uid = uuid.UUID(uid)
        elif isinstance(uid, uuid.UUID):
            pass
        else:
            raise ValueError('Invalid folder id')

        return Folder[uid]

    @staticmethod
    def add(name, path):
        if Folder.get(name = name, root = True) is not None:
            raise ValueError("Folder '{}' exists".format(name))

        path = os.path.abspath(path)
        if not os.path.isdir(path):
            raise ValueError("The path doesn't exits or is'nt a directory")
        if Folder.get(path = path) is not None:
            raise ValueError('This path is already registered')
        if any(path.startswith(p) for p in select(f.path for f in Folder if f.root)):
            raise ValueError('This path is already registered')
        if Folder.exists(lambda f: f.path.startswith(path)):
            raise ValueError('This path contains a folder that is already registered')

        return Folder(root = True, name = name, path = path)

    @staticmethod
    def delete(uid):
        folder = FolderManager.get(uid)
        if not folder.root:
            raise ObjectNotFound(Folder)

        Track.select(lambda t: t.root_folder == folder).delete(bulk = True)
        Album.prune()
        Artist.prune()
        Folder.select(lambda f: not f.root and f.path.startswith(folder.path)).delete(bulk = True)

        folder.delete()

    @staticmethod
    def delete_by_name(name):
        folder = Folder.get(name = name, root = True)
        if not folder:
            raise ObjectNotFound(Folder)
        FolderManager.delete(folder.id)


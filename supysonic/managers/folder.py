# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2018  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import uuid

from pony.orm import select
from pony.orm import ObjectNotFound

from ..db import Folder, Track
from ..py23 import strtype
from ..scanner import Scanner

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

        scanner = Scanner()
        for track in Track.select(lambda t: t.root_folder == folder):
            scanner.remove_file(track.path)
        scanner.finish()

        folder.delete()

    @staticmethod
    def delete_by_name(name):
        folder = Folder.get(name = name, root = True)
        if not folder:
            raise ObjectNotFound(Folder)
        FolderManager.delete(folder.id)


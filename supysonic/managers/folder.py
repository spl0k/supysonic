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

from pony.orm import db_session, select
from pony.orm import ObjectNotFound

from ..db import Folder, Artist, Album, Track, StarredFolder, RatingFolder
from ..py23 import strtype
from ..scanner import Scanner

class FolderManager:
    SUCCESS = 0
    INVALID_ID = 1
    NAME_EXISTS = 2
    INVALID_PATH = 3
    PATH_EXISTS = 4
    NO_SUCH_FOLDER = 5
    SUBPATH_EXISTS = 6

    @staticmethod
    @db_session
    def get(uid):
        if isinstance(uid, strtype):
            try:
                uid = uuid.UUID(uid)
            except ValueError:
                return FolderManager.INVALID_ID, None
        elif isinstance(uid, uuid.UUID):
            pass
        else:
            return FolderManager.INVALID_ID, None

        try:
            folder = Folder[uid]
            return FolderManager.SUCCESS, folder
        except ObjectNotFound:
            return FolderManager.NO_SUCH_FOLDER, None

    @staticmethod
    @db_session
    def add(name, path):
        if Folder.get(name = name, root = True) is not None:
            return FolderManager.NAME_EXISTS

        path = os.path.abspath(path)
        if not os.path.isdir(path):
            return FolderManager.INVALID_PATH
        if Folder.get(path = path) is not None:
            return FolderManager.PATH_EXISTS
        if any(path.startswith(p) for p in select(f.path for f in Folder)):
            return FolderManager.PATH_EXISTS
        if Folder.exists(lambda f: f.path.startswith(path)):
            return FolderManager.SUBPATH_EXISTS

        folder = Folder(root = True, name = name, path = path)
        return FolderManager.SUCCESS

    @staticmethod
    @db_session
    def delete(uid):
        status, folder = FolderManager.get(uid)
        if status != FolderManager.SUCCESS:
            return status

        if not folder.root:
            return FolderManager.NO_SUCH_FOLDER

        scanner = Scanner()
        for track in Track.select(lambda t: t.root_folder == folder):
            scanner.remove_file(track.path)
        scanner.finish()

        folder.delete()
        return FolderManager.SUCCESS

    @staticmethod
    @db_session
    def delete_by_name(name):
        folder = Folder.get(name = name, root = True)
        if not folder:
            return FolderManager.NO_SUCH_FOLDER
        return FolderManager.delete(folder.id)

    @staticmethod
    def error_str(err):
        if err == FolderManager.SUCCESS:
            return 'No error'
        elif err == FolderManager.INVALID_ID:
            return 'Invalid folder id'
        elif err == FolderManager.NAME_EXISTS:
            return 'There is already a folder with that name. Please pick another one.'
        elif err == FolderManager.INVALID_PATH:
            return "The path doesn't exists or isn't a directory"
        elif err == FolderManager.PATH_EXISTS:
            return 'This path is already registered'
        elif err == FolderManager.NO_SUCH_FOLDER:
            return 'No such folder'
        elif err == FolderManager.SUBPATH_EXISTS:
            return 'This path contains a folder that is already registered'
        return 'Unknown error'


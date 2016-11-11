# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013, 2014  Alban 'spl0k' Féron
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

import os.path, uuid
from supysonic.db import Folder, Artist, Album, Track
from supysonic.scanner import Scanner

class FolderManager:
	SUCCESS = 0
	INVALID_ID = 1
	NAME_EXISTS = 2
	INVALID_PATH = 3
	PATH_EXISTS = 4
	NO_SUCH_FOLDER = 5
	SUBPATH_EXISTS = 6

	@staticmethod
	def get(store, uid):
		if isinstance(uid, basestring):
			try:
				uid = uuid.UUID(uid)
			except:
				return FolderManager.INVALID_ID, None
		elif type(uid) is uuid.UUID:
			pass
		else:
			return FolderManager.INVALID_ID, None

		folder = store.get(Folder, uid)
		if not folder:
			return FolderManager.NO_SUCH_FOLDER, None

		return FolderManager.SUCCESS, folder

	@staticmethod
	def add(store, name, path):
		if not store.find(Folder, Folder.name == name, Folder.root == True).is_empty():
			return FolderManager.NAME_EXISTS

		path = unicode(os.path.abspath(path))
		if not os.path.isdir(path):
			return FolderManager.INVALID_PATH
		if not store.find(Folder, Folder.path == path).is_empty():
			return FolderManager.PATH_EXISTS
		if any(path.startswith(p) for p in store.find(Folder).values(Folder.path)):
			return FolderManager.PATH_EXISTS
		if not store.find(Folder, Folder.path.startswith(path)).is_empty():
			return FolderManager.SUBPATH_EXISTS

		folder = Folder()
		folder.root = True
		folder.name = name
		folder.path = path

		store.add(folder)
		store.commit()

		return FolderManager.SUCCESS

	@staticmethod
	def delete(store, uid):
		status, folder = FolderManager.get(store, uid)
		if status != FolderManager.SUCCESS:
			return status

		if not folder.root:
			return FolderManager.NO_SUCH_FOLDER

		scanner = Scanner(store)
		for track in store.find(Track, Track.root_folder_id == folder.id):
			scanner.remove_file(track.path)
		scanner.finish()

		store.find(StarredFolder, StarredFolder.starred_id == uid).remove()
		store.find(RatingFolder, RatingFolder.rated_id == uid).remove()

		store.remove(folder)
		store.commit()

		return FolderManager.SUCCESS

	@staticmethod
	def delete_by_name(store, name):
		folder = store.find(Folder, Folder.name == name, Folder.root == True).one()
		if not folder:
			return FolderManager.NO_SUCH_FOLDER
		return FolderManager.delete(store, folder.id)

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


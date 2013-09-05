# coding: utf-8

import os.path, uuid
from db import Folder, Artist, session

class FolderManager:
	SUCCESS = 0
	INVALID_ID = 1
	NAME_EXISTS = 2
	INVALID_PATH = 3
	PATH_EXISTS = 4
	NO_SUCH_FOLDER = 5

	@staticmethod
	def get(uid):
		if isinstance(uid, basestring):
			try:
				uid = uuid.UUID(uid)
			except:
				return FolderManager.INVALID_ID, None
		elif type(uid) is uuid.UUID:
			pass
		else:
			return FolderManager.INVALID_ID, None

		folder = Folder.query.get(uid)
		if not folder:
			return FolderManager.NO_SUCH_FOLDER, None

		return FolderManager.SUCCESS, folder

	@staticmethod
	def add(name, path):
		if Folder.query.filter(Folder.name == name and Folder.root == True).first():
			return FolderManager.NAME_EXISTS

		path = os.path.abspath(path)
		if not os.path.isdir(path):
			return FolderManager.INVALID_PATH
		folder = Folder.query.filter(Folder.path == path).first()
		if folder:
			return FolderManager.PATH_EXISTS

		folder = Folder(root = True, name = name, path = path)
		session.add(folder)
		session.commit()

		return FolderManager.SUCCESS

	@staticmethod
	def delete(uid):
		status, folder = FolderManager.get(uid)
		if status != FolderManager.SUCCESS:
			return status

		if not folder.root:
			return FolderManager.NO_SUCH_FOLDER

		# delete associated tracks and prune empty albums/artists
		for artist in Artist.query.all():
			for album in artist.albums[:]:
				for track in filter(lambda t: t.root_folder.id == folder.id, album.tracks):
					album.tracks.remove(track)
					session.delete(track)
				if len(album.tracks) == 0:
					artist.albums.remove(album)
					session.delete(album)
			if len(artist.albums) == 0:
				session.delete(artist)

		def cleanup_folder(folder):
			for f in folder.children:
				cleanup_folder(f)
			session.delete(folder)

		cleanup_folder(folder)
		session.commit()

		return FolderManager.SUCCESS

	@staticmethod
	def delete_by_name(name):
		folder = Folder.query.filter(Folder.name == name and Folder.root == True).first()
		if not folder:
			return FolderManager.NO_SUCH_FOLDER
		return FolderManager.delete(folder.id)

	@staticmethod
	def scan(uid, scanner):
		status, folder = FolderManager.get(uid)
		if status != FolderManager.SUCCESS:
			return status

		scanner.scan(folder)
		scanner.prune(folder)
		scanner.check_cover_art(folder)
		return FolderManager.SUCCESS

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
		return 'Unknown error'


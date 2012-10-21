# coding: utf-8

import os, os.path
import datetime
import eyeD3

import db

class Scanner:
	def __init__(self, session):
		self.__session = session
		self.__artists = db.Artist.query.all()
		self.__folders = db.Folder.query.all()

		self.__added_artists = 0
		self.__added_albums = 0
		self.__added_tracks = 0
		self.__deleted_artists = 0
		self.__deleted_albums = 0
		self.__deleted_tracks = 0

	def scan(self, folder):
		for root, subfolders, files in os.walk(folder.path):
			for f in files:
				if f.endswith('.mp3'):
					self.__scan_file(os.path.join(root, f), folder)
		folder.last_scan = datetime.datetime.now()

	def prune(self, folder):
		for artist in db.Artist.query.all():
			for album in artist.albums[:]:
				for track in filter(lambda t: t.root_folder.id == folder.id, album.tracks):
					if not os.path.exists(track.path):
						album.tracks.remove(track)
						track.folder.tracks.remove(track)
						self.__session.delete(track)
						self.__deleted_tracks += 1
				if len(album.tracks) == 0:
					artist.albums.remove(album)
					self.__session.delete(album)
					self.__deleted_albums += 1
			if len(artist.albums) == 0:
				self.__session.delete(artist)
				self.__deleted_artists += 1

		self.__cleanup_folder(folder)

	def __scan_file(self, path, folder):
		tag = eyeD3.Tag()
		tag.link(path)
		audio_file = eyeD3.Mp3AudioFile(path)

		al = self.__find_album(tag.getArtist(), tag.getAlbum())
		tr = filter(lambda t: t.path == path, al.tracks)
		if not tr:
			tr = db.Track(path = path, root_folder = folder, folder = self.__find_folder(path, folder))
			self.__added_tracks += 1
		else:
			tr = tr[0]

		tr.disc = (tag.getDiscNum() or (1, 1))[0]
		tr.number = tag.getTrackNum()[0]
		tr.title = tag.getTitle()
		tr.year = tag.getYear()
		tr.genre = tag.getGenre().name if tag.getGenre() else None
		tr.duration = audio_file.getPlayTime()
		tr.album = al
		tr.bitrate = audio_file.getBitRate()[1]

	def __find_album(self, artist, album):
		ar = self.__find_artist(artist)
		al = filter(lambda a: a.name == album, ar.albums)
		if al:
			return al[0]

		al = db.Album(name = album, artist = ar)
		self.__added_albums += 1

		return al

	def __find_artist(self, artist):
		ar = filter(lambda a: a.name == artist, self.__artists)
		if ar:
			return ar[0]

		ar = db.Artist(name = artist)
		self.__artists.append(ar)
		self.__session.add(ar)
		self.__added_artists += 1

		return ar

	def __find_folder(self, path, folder):
		path = os.path.dirname(path)
		fold = filter(lambda f: f.path == path, self.__folders)
		if fold:
			return fold[0]

		full_path = folder.path
		path = path[len(folder.path) + 1:]

		for name in path.split(os.sep):
			full_path = os.path.join(full_path, name)
			fold = filter(lambda f: f.path == full_path, self.__folders)
			if fold:
				folder = fold[0]
			else:
				folder = db.Folder(root = False, name = name, path = full_path, parent = folder)
				self.__folders.append(folder)

		return folder

	def __cleanup_folder(self, folder):
		for f in folder.children:
			self.__cleanup_folder(f)
		if len(folder.children) == 0 and len(folder.tracks) == 0 and not folder.root:
			folder.parent = None
			self.__session.delete(folder)

	def stats(self):
		return (self.__added_artists, self.__added_albums, self.__added_tracks), (self.__deleted_artists, self.__deleted_albums, self.__deleted_tracks)


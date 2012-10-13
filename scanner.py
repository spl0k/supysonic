# coding: utf-8

import os.path
import datetime
import eyeD3

import db

def seconds_to_time(secs):
	th = secs / 3600
	tm = (secs % 3600) / 60
	ts = secs % 60
	return datetime.time(int(th), int(tm), int(ts))

class Scanner:
	def __init__(self, session):
		self.__session = session
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
					self.__scan_file(os.path.join(root, f))

	def prune(self, folder):
		pass

	def __scan_file(self, path):
		tag = eyeD3.Tag()
		tag.link(path)

		al = self.__find_album(tag.getArtist(), tag.getAlbum())
		tr = al.tracks.filter(db.Track.path == path).first()
		if tr is None:
			tr = db.Track(path = path)
			self.__added_tracks += 1

		tr.disc = (tag.getDiscNum() or (1, 1))[0]
		tr.number = tag.getTrackNum()[0]
		tr.title = tag.getTitle()
		tr.duration = seconds_to_time(eyeD3.Mp3AudioFile(path).getPlayTime())
		tr.album = al

	def __find_album(self, artist, album):
		ar = self.__find_artist(artist)
		al = ar.albums.filter(db.Album.name == album).first()
		if not al is None:
			return al

		al = db.Album(name = album, artist = ar)
		self.__added_albums += 1

		return al

	def __find_artist(self, artist):
		ar = self.__session.query(db.Artist).filter(db.Artist.name == artist).first()
		if not ar is None:
			return ar

		ar = db.Artist(name = artist)
		self.__session.add(ar)
		self.__added_artists += 1

		return ar

	def stats(self):
		return (self.__added_artists, self.__added_albums, self.__added_tracks), (self.__deleted_artists, self.__deleted_albums, self.__deleted_tracks)


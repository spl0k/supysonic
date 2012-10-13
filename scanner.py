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
		self.__artists = db.Artist.query.all()
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
		for artist in db.Artist.query.all():
			for album in artist.albums[:]:
				for track in album.tracks[:]:
					if not os.path.exists(track.path):
						album.tracks.remove(track)
						self.__session.delete(track)
						self.__deleted_tracks += 1
				if len(album.tracks) == 0:
					artist.albums.remove(album)
					self.__session.delete(album)
					self.__deleted_albums += 1
			if len(artist.albums) == 0:
				self.__session.delete(artist)
				self.__deleted_artists += 1

	def __scan_file(self, path):
		tag = eyeD3.Tag()
		tag.link(path)

		al = self.__find_album(tag.getArtist(), tag.getAlbum())
		tr = filter(lambda t: t.path == path, al.tracks)
		if not tr:
			tr = db.Track(path = path)
			self.__added_tracks += 1
		else:
			tr = tr[0]

		tr.disc = (tag.getDiscNum() or (1, 1))[0]
		tr.number = tag.getTrackNum()[0]
		tr.title = tag.getTitle()
		tr.duration = seconds_to_time(eyeD3.Mp3AudioFile(path).getPlayTime())
		tr.album = al

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

	def stats(self):
		return (self.__added_artists, self.__added_albums, self.__added_tracks), (self.__deleted_artists, self.__deleted_albums, self.__deleted_tracks)


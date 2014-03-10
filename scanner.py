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

import os, os.path
import time, mimetypes
import mutagen
import config
from db import Folder, Artist, Album, Track

def get_mime(ext):
	return mimetypes.guess_type('dummy.' + ext, False)[0] or config.get('mimetypes', ext) or 'application/octet-stream'

class Scanner:
	def __init__(self, store):
		self.__store = store

		self.__added_artists = 0
		self.__added_albums  = 0
		self.__added_tracks  = 0
		self.__deleted_artists = 0
		self.__deleted_albums  = 0
		self.__deleted_tracks  = 0

		extensions = config.get('base', 'scanner_extensions')
		self.__extensions = map(str.lower, extensions.split()) if extensions else None

	def scan(self, folder, progress_callback = None):
		files = [ os.path.join(root, f) for root, _, fs in os.walk(folder.path) for f in fs if self.__is_valid_path(os.path.join(root, f)) ]
		total = len(files)
		current = 0

		for path in files:
			self.__scan_file(path, folder)
			current += 1
			if progress_callback:
				progress_callback(current, total)

		folder.last_scan = int(time.time())

		self.__store.flush()

	def prune(self, folder):
		for track in [ t for t in self.__store.find(Track, Track.root_folder_id == folder.id) if not self.__is_valid_path(t.path) ]:
			self.__store.remove(track)
			self.__deleted_tracks += 1

		# TODO execute the conditional part on SQL
		for album in [ a for a in self.__store.find(Album) if a.tracks.count() == 0 ]:
			self.__store.remove(album)
			self.__deleted_albums += 1

		# TODO execute the conditional part on SQL
		for artist in [ a for a in self.__store.find(Artist) if a.albums.count() == 0 ]:
			self.__store.remove(artist)
			self.__deleted_artists += 1

		self.__cleanup_folder(folder)
		self.__store.flush()

	def check_cover_art(self, folder):
		folder.has_cover_art = os.path.isfile(os.path.join(folder.path, 'cover.jpg'))
		for f in folder.children:
			self.check_cover_art(f)

	def __is_valid_path(self, path):
		if not os.path.exists(path):
			return False
		if not self.__extensions:
			return True
		return os.path.splitext(path)[1][1:].lower() in self.__extensions

	def __scan_file(self, path, folder):
		tr = self.__store.find(Track, Track.path == path).one()
		if tr:
			if not os.path.getmtime(path) > tr.last_modification:
				return

			tag = self.__try_load_tag(path)
			if not tag:
				self.__store.remove(tr)
				self.__deleted_tracks += 1
				return
		else:
			tag = self.__try_load_tag(path)
			if not tag:
				return

			tr = Track()
			tr.path = path
			tr.root_folder = folder
			tr.folder = self.__find_folder(path, folder)

			self.__store.add(tr)
			self.__added_tracks += 1

		tr.disc     = self.__try_read_tag(tag, 'discnumber',  1, lambda x: int(x[0].split('/')[0]))
		tr.number   = self.__try_read_tag(tag, 'tracknumber', 1, lambda x: int(x[0].split('/')[0]))
		tr.title    = self.__try_read_tag(tag, 'title', '')
		tr.year     = self.__try_read_tag(tag, 'date', None, lambda x: int(x[0].split('-')[0]))
		tr.genre    = self.__try_read_tag(tag, 'genre')
		tr.duration = int(tag.info.length)
		tr.album    = self.__find_album(self.__try_read_tag(tag, 'artist', ''), self.__try_read_tag(tag, 'album', ''))
		tr.bitrate  = (tag.info.bitrate if hasattr(tag.info, 'bitrate') else int(os.path.getsize(path) * 8 / tag.info.length)) / 1000
		tr.content_type = get_mime(os.path.splitext(path)[1][1:])
		tr.last_modification = os.path.getmtime(path)

	def __find_album(self, artist, album):
		ar = self.__find_artist(artist)
		al = ar.albums.find(name = album).one()
		if al:
			return al

		al = Album()
		al.name = album
		al.artist = ar

		self.__store.add(al)
		self.__added_albums += 1

		return al

	def __find_artist(self, artist):
		ar = self.__store.find(Artist, Artist.name == artist).one()
		if ar:
			return ar

		ar = Artist()
		ar.name = artist

		self.__store.add(ar)
		self.__added_artists += 1

		return ar

	def __find_folder(self, path, folder):
		path = os.path.dirname(path)
		fold = self.__store.find(Folder, Folder.path == path).one()
		if fold:
			return fold

		full_path = folder.path
		path = path[len(folder.path) + 1:]

		for name in path.split(os.sep):
			full_path = os.path.join(full_path, name)
			fold = self.__store.find(Folder, Folder.path == full_path).one()
			if not fold:
				fold = Folder()
				fold.root = False
				fold.name = name
				fold.path = full_path
				fold.parent = folder

				self.__store.add(fold)

			folder = fold

		return folder

	def __try_load_tag(self, path):
		try:
			return mutagen.File(path, easy = True)
		except:
			return None

	def __try_read_tag(self, metadata, field, default = None, transform = lambda x: x[0]):
		try:
			value = metadata[field]
			if not value:
				return default
			if transform:
				value = transform(value)
				return value if value else default
		except:
			return default

	def __cleanup_folder(self, folder):
		for f in folder.children:
			self.__cleanup_folder(f)
		if folder.children.count() == 0 and folder.tracks.count() == 0 and not folder.root:
			self.__store.remove(folder)

	def stats(self):
		return (self.__added_artists, self.__added_albums, self.__added_tracks), (self.__deleted_artists, self.__deleted_albums, self.__deleted_tracks)


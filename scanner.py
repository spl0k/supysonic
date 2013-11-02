# coding: utf-8

import os, os.path
import time, mimetypes
import mutagen
import config, db

def get_mime(ext):
	return mimetypes.guess_type('dummy.' + ext, False)[0] or config.get('mimetypes', ext) or 'application/octet-stream'

class Scanner:
	def __init__(self, session):
		self.__session = session
		self.__tracks  = db.Track.query.all()
		self.__artists = db.Artist.query.all()
		self.__folders = db.Folder.query.all()

		self.__added_artists = 0
		self.__added_albums  = 0
		self.__added_tracks  = 0
		self.__deleted_artists = 0
		self.__deleted_albums  = 0
		self.__deleted_tracks  = 0

		extensions = config.get('base', 'scanner_extensions')
		self.__extensions = map(str.lower, extensions.split()) if extensions else None

	def scan(self, folder):
		for root, subfolders, files in os.walk(folder.path):
			for f in files:
				path = os.path.join(root, f)
				if self.__is_valid_path(path):
					self.__scan_file(path, folder)
		folder.last_scan = int(time.time())

	def prune(self, folder):
		for track in [ t for t in self.__tracks if t.root_folder.id == folder.id and not self.__is_valid_path(t.path) ]:
			self.__remove_track(track)

		for album in [ album for artist in self.__artists for album in artist.albums if len(album.tracks) == 0 ]:
			album.artist.albums.remove(album)
			self.__session.delete(album)
			self.__deleted_albums += 1

		for artist in [ a for a in self.__artists if len(a.albums) == 0 ]:
			self.__session.delete(artist)
			self.__deleted_artists += 1

		self.__cleanup_folder(folder)

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
		tr = filter(lambda t: t.path == path, self.__tracks)
		if tr:
			tr = tr[0]
			if not os.path.getmtime(path) > tr.last_modification:
				return

			tag = self.__try_load_tag(path)
			if not tag:
				self.__remove_track(tr)
				return
		else:
			tag = self.__try_load_tag(path)
			if not tag:
				return

			tr = db.Track(path = path, root_folder = folder, folder = self.__find_folder(path, folder))
			self.__tracks.append(tr)
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
		al = filter(lambda a: a.name == album, ar.albums)
		if al:
			return al[0]

		al = db.Album(name = album, artist = ar)
		self.__added_albums += 1

		return al

	def __find_artist(self, artist):
		ar = filter(lambda a: a.name.lower() == artist.lower(), self.__artists)
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

	def __remove_track(self, track):
		track.album.tracks.remove(track)
		track.folder.tracks.remove(track)
		# As we don't have a track -> playlists relationship, SQLAlchemy doesn't know it has to remove tracks
		# from playlists as well, so let's help it
		for playlist in db.Playlist.query.filter(db.Playlist.tracks.contains(track)):
			playlist.tracks.remove(track)
		self.__session.delete(track)
		self.__deleted_tracks += 1

	def __cleanup_folder(self, folder):
		for f in folder.children:
			self.__cleanup_folder(f)
		if len(folder.children) == 0 and len(folder.tracks) == 0 and not folder.root:
			folder.parent = None
			self.__session.delete(folder)

	def stats(self):
		return (self.__added_artists, self.__added_albums, self.__added_tracks), (self.__deleted_artists, self.__deleted_albums, self.__deleted_tracks)


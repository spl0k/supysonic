# coding: utf-8

import os, os.path
import time
import mutagen
import config, db
import math
import sys, traceback
from web import app

class Scanner:
	def __init__(self, session):
		self.__session = session

		self.__tracks  = db.Track.query.all()
		self.__tracks = {x.path: x for x in self.__tracks}

		self.__artists = db.Artist.query.all()
		self.__artists = {x.name.lower(): x for x in self.__artists}

		self.__folders = db.Folder.query.all()
		self.__folders = {x.path: x for x in self.__folders}

		self.__playlists = db.Playlist.query.all()

		self.__added_artists = 0
		self.__added_albums  = 0
		self.__added_tracks  = 0
		self.__deleted_artists = 0
		self.__deleted_albums  = 0
		self.__deleted_tracks  = 0

		extensions = config.get('base', 'scanner_extensions')
		self.__extensions = map(str.lower, extensions.split()) if extensions else None

	def scan(self, folder):
		print "scanning", folder.path
		valid = [x.lower() for x in config.get('base','filetypes').split(',')]
		valid = tuple(valid)
		print "valid filetypes: ",valid

		for root, subfolders, files in os.walk(folder.path, topdown=False):
			for f in files:
				if f.lower().endswith(valid):
					try:
						self.__scan_file(os.path.join(root, f), folder)
					except:
						app.logger.error('Problem adding file: ' + os.path.join(root,f))
						app.logger.error(traceback.print_exc())
						sys.exit(0)
						self.__session.rollback()

		print "\a"
		self.__session.add_all(self.__tracks.values())
		self.__session.commit()
		folder.last_scan = int(time.time())

	def prune(self, folder):
		for path, root_folder_id, track_id in self.__session.query(db.Track.path, db.Track.root_folder_id, db.Track.id):
			if root_folder_id == folder.id and not os.path.exists(path):
				app.logger.debug('Removed invalid path: ' + path)
				self.__remove_track(self.__session.merge(db.Track(id = track_id)))

		self.__session.commit()

		for album in [ album for artist in self.__artists.values() for album in artist.albums if len(album.tracks) == 0 ]:
			album.artist.albums.remove(album)
			self.__session.delete(album)
			self.__deleted_albums += 1

		self.__session.commit()

		for artist in [ a for a in self.__artists.values() if len(a.albums) == 0 ]:
			self.__session.delete(artist)
			self.__deleted_artists += 1

		self.__session.commit()

		self.__cleanup_folder(folder)

	def __scan_file(self, path, folder):
		curmtime = int(math.floor(os.path.getmtime(path)))

		if path in self.__tracks:
			tr = self.__tracks[path]

			app.logger.debug('Existing File: ' + path)
			if not tr.last_modification:
				tr.last_modification = curmtime

			if curmtime <= tr.last_modification:
				app.logger.debug('\tFile not modified')
				return False

			app.logger.debug('\tFile modified, updating tag')
			app.logger.debug('\tcurmtime %s / last_mod %s', curmtime, tr.last_modification)
			app.logger.debug('\t\t%s Seconds Newer\n\t\t', str(curmtime - tr.last_modification))
			tag = self.__try_load_tag(path)
			if not tag:
				app.logger.debug('\tError retrieving tags, removing track from DB')
				self.__remove_track(tr)
				return False
		else:
			app.logger.debug('Scanning File: ' + path + '\n\tReading tag')
			tag = self.__try_load_tag(path)
			if not tag:
				app.logger.debug('\tProblem reading tag')
				return False

			tr = db.Track(path = path, root_folder = folder, folder = self.__find_folder(path, folder))

			self.__tracks[path] = tr
			self.__added_tracks += 1

		tr.last_modification = curmtime
		tr.disc     = self.__try_read_tag(tag, 'discnumber',  1, lambda x: int(x[0].split('/')[0]))
		tr.number   = self.__try_read_tag(tag, 'tracknumber', 1, lambda x: int(x[0].split('/')[0]))
		tr.title    = self.__try_read_tag(tag, 'title', '')
		tr.year     = self.__try_read_tag(tag, 'date', None, lambda x: int(x[0].split('-')[0]))
		tr.genre    = self.__try_read_tag(tag, 'genre')
		tr.duration = int(tag.info.length)

		# TODO: use album artist if available, then artist, then unknown
		tr.album    = self.__find_album(self.__try_read_tag(tag, 'artist', 'Unknown'), self.__try_read_tag(tag, 'album', 'Unknown'))

		tr.bitrate  = (tag.info.bitrate if hasattr(tag.info, 'bitrate') else int(os.path.getsize(path) * 8 / tag.info.length)) / 1000

		return True

	def __find_album(self, artist, album):
		# TODO : DB specific issues with single column name primary key
		#		for instance, case sensitivity and trailing spaces
		artist = artist.rstrip()

		if artist in self.__artists:
			ar = self.__artists[artist]
		else:
			#Flair!
			sys.stdout.write('\033[K')
			sys.stdout.write('%s\r' % artist)
			sys.stdout.flush()
			ar = db.Artist(name = artist)
			self.__artists[artist] = ar
			self.__added_artists += 1

		al = {a.name: a for a in ar.albums}
		if album in al:
			return al[album]
		else:
			self.__added_albums += 1
			return db.Album(name = album, artist = ar)

	def __find_folder(self, path, folder):

		path = os.path.dirname(path)
		if path in self.__folders:
			return self.__folders[path]

		# must find parent directory to create new one
		full_path = folder.path
		path = path[len(folder.path) + 1:]

		for name in path.split(os.sep):
			full_path = os.path.join(full_path, name)

			if full_path in self.__folders:
				folder = self.__folders[full_path]
			else:
				folder = db.Folder(root = False, name = name, path = full_path, parent = folder)
				self.__folders[full_path] = folder

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
		for playlist in self.__playlists:
			if track in playlist.tracks:
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


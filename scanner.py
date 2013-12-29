# coding: utf-8

import os, os.path
import time
import mutagen
import config
import math
import sys, traceback
from web import app
import db

class Scanner:
	def __init__(self, session):
		self.__session = session

		self.__tracks  = db.Track.query.all()
		self.__tracks = {x.path: x for x in self.__tracks}
		self.__tracktimes = {x.path: x.last_modification for x in self.__tracks.values()}

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

	def scan(self, root_folder):
		print "scanning", root_folder.path
		valid = [x.lower() for x in config.get('base','filetypes').split(',')]
		valid = tuple(valid)
		print "valid filetypes: ",valid

		for root, subfolders, files in os.walk(root_folder.path, topdown=False):
			if(root not in self.__folders):
				app.logger.debug('Adding folder (empty): ' + root)
				self.__folders[root] = db.Folder(path = root)

			for f in files:
				if f.lower().endswith(valid):
					try:
						path = os.path.join(root, f)
						self.__scan_file(path, root)
					except:
						app.logger.error('Problem adding file: ' + os.path.join(root,f))
						app.logger.error(traceback.print_exc())
						sys.exit(0)
						self.__session.rollback()

		self.__session.add_all(self.__folders.values())
		self.__session.add_all(self.__tracks.values())
		root_folder.last_scan = int(time.time())
		self.__session.commit()

	def prune(self, folder):
		# check for invalid paths still in database
		#app.logger.debug('Checking for invalid paths...')
		#for path in self.__tracks.keys():
			#if not os.path.exists(path.encode('utf-8')):
				#app.logger.debug('Removed invalid path: ' + path)
				#self.__remove_track(self.__tracks[path])

		app.logger.debug('Checking for empty albums...')
		for album in db.Album.query.filter(~db.Album.id.in_(self.__session.query(db.Track.album_id).distinct())):
			app.logger.debug(album.name + ' Removed')
			album.artist.albums.remove(album)
			self.__session.delete(album)
			self.__deleted_albums += 1

		app.logger.debug('Checking for artists with no albums...')
		for artist in [ a for a in self.__artists.values() if len(a.albums) == 0 ]:
			self.__session.delete(artist)
			self.__deleted_artists += 1

		self.__session.commit()

		app.logger.debug('Cleaning up folder...')
		self.__cleanup_folder(folder)

	def __scan_file(self, path, root):
		curmtime = int(math.floor(os.path.getmtime(path)))

		if path in self.__tracks:
			tr = self.__tracks[path]

			app.logger.debug('Existing File: ' + path)
			if not tr.last_modification:
				tr.last_modification = curmtime

			if curmtime <= self.__tracktimes[path]:
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

			tr = db.Track(path = path, folder = self.__find_folder(root))

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
			sys.stdout.write('%s\r' % artist.encode('utf-8'))
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

	def __find_folder(self, path):

		if path in self.__folders:
			return self.__folders[path]

		app.logger.debug('Adding folder: ' + path)
		self.__folders[path] = db.Folder(path = path)
		return self.__folders[path]

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


		# Get all subfolders of folder
		all_descendants = self.__session.query(db.Folder).filter(db.Folder.path.like(folder.path + os.sep + '%'))

		app.logger.debug('Checking for empty paths')

		# Delete folder if there is no track in a subfolder
		for d in all_descendants:
			if any(d.path in k for k in self.__tracks.keys()):
				continue;
			else:
				app.logger.debug('Deleting path with no tracks: ' + d.path)
				self.__session.delete(d)

		self.__session.commit()
		return

	def stats(self):
		return (self.__added_artists, self.__added_albums, self.__added_tracks), (self.__deleted_artists, self.__deleted_albums, self.__deleted_tracks)


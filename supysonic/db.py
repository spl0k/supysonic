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

from storm.properties import *
from storm.references import Reference, ReferenceSet
from storm.database import create_database
from storm.store import Store
from storm.variables import Variable

import uuid, datetime, time
import os.path

from supysonic import config

def now():
	return datetime.datetime.now().replace(microsecond = 0)

class UnicodeOrStrVariable(Variable):
	__slots__ = ()

	def parse_set(self, value, from_db):
		if isinstance(value, unicode):
			return value
		elif isinstance(value, str):
			return unicode(value)
		raise TypeError("Expected unicode, found %r: %r" % (type(value), value))

Unicode.variable_class = UnicodeOrStrVariable

class Folder(object):
	__storm_table__ = 'folder'

	id = UUID(primary = True, default_factory = uuid.uuid4)
	root = Bool(default = False)
	name = Unicode()
	path = Unicode() # unique
	created = DateTime(default_factory = now)
	has_cover_art = Bool(default = False)
	last_scan = Int(default = 0)

	parent_id = UUID() # nullable
	parent = Reference(parent_id, id)
	children = ReferenceSet(id, parent_id)

	def as_subsonic_child(self, user):
		info = {
			'id': str(self.id),
			'isDir': True,
			'title': self.name,
			'album': self.name,
			'created': self.created.isoformat()
		}
		if not self.root:
			info['parent'] = str(self.parent_id)
			info['artist'] = self.parent.name
		if self.has_cover_art:
			info['coverArt'] = str(self.id)

		starred = Store.of(self).get(StarredFolder, (user.id, self.id))
		if starred:
			info['starred'] = starred.date.isoformat()

		rating = Store.of(self).get(RatingFolder, (user.id, self.id))
		if rating:
			info['userRating'] = rating.rating
		avgRating = Store.of(self).find(RatingFolder, RatingFolder.rated_id == self.id).avg(RatingFolder.rating)
		if avgRating:
			info['averageRating'] = avgRating

		return info

class Artist(object):
	__storm_table__ = 'artist'

	id = UUID(primary = True, default_factory = uuid.uuid4)
	name = Unicode() # unique

	def as_subsonic_artist(self, user):
		info = {
			'id': str(self.id),
			'name': self.name,
			# coverArt
			'albumCount': self.albums.count()
		}

		starred = Store.of(self).get(StarredArtist, (user.id, self.id))
		if starred:
			info['starred'] = starred.date.isoformat()

		return info

class Album(object):
	__storm_table__ = 'album'

	id = UUID(primary = True, default_factory = uuid.uuid4)
	name = Unicode()
	artist_id = UUID()
	artist = Reference(artist_id, Artist.id)

	def as_subsonic_album(self, user):
		info = {
			'id': str(self.id),
			'name': self.name,
			'artist': self.artist.name,
			'artistId': str(self.artist_id),
			'songCount': self.tracks.count(),
			'duration': sum(self.tracks.values(Track.duration)),
			'created': min(self.tracks.values(Track.created)).isoformat()
		}

		track_with_cover = self.tracks.find(Track.folder_id == Folder.id, Folder.has_cover_art).any()
		if track_with_cover:
			info['coverArt'] = str(track_with_cover.folder_id)

		starred = Store.of(self).get(StarredAlbum, (user.id, self.id))
		if starred:
			info['starred'] = starred.date.isoformat()

		return info

	def sort_key(self):
		year = min(map(lambda t: t.year if t.year else 9999, self.tracks))
		return '%i%s' % (year, self.name.lower())

Artist.albums = ReferenceSet(Artist.id, Album.artist_id)

class Track(object):
	__storm_table__ = 'track'

	id = UUID(primary = True, default_factory = uuid.uuid4)
	disc = Int()
	number = Int()
	title = Unicode()
	year = Int() # nullable
	genre = Unicode() # nullable
	duration = Int()
	album_id = UUID()
	album = Reference(album_id, Album.id)
	artist_id = UUID()
	artist = Reference(artist_id, Artist.id)
	bitrate = Int()

	path = Unicode() # unique
	content_type = Unicode()
	created = DateTime(default_factory = now)
	last_modification = Int()

	play_count = Int(default = 0)
	last_play = DateTime() # nullable

	root_folder_id = UUID()
	root_folder = Reference(root_folder_id, Folder.id)
	folder_id = UUID()
	folder = Reference(folder_id, Folder.id)

	def as_subsonic_child(self, user, prefs):
		info = {
			'id': str(self.id),
			'parent': str(self.folder_id),
			'isDir': False,
			'title': self.title,
			'album': self.album.name,
			'artist': self.artist.name,
			'track': self.number,
			'size': os.path.getsize(self.path),
			'contentType': self.content_type,
			'suffix': self.suffix(),
			'duration': self.duration,
			'bitRate': self.bitrate,
			'path': self.path[len(self.root_folder.path) + 1:],
			'isVideo': False,
			'discNumber': self.disc,
			'created': self.created.isoformat(),
			'albumId': str(self.album_id),
			'artistId': str(self.artist_id),
			'type': 'music'
		}

		if self.year:
			info['year'] = self.year
		if self.genre:
			info['genre'] = self.genre
		if self.folder.has_cover_art:
			info['coverArt'] = str(self.folder_id)

		starred = Store.of(self).get(StarredTrack, (user.id, self.id))
		if starred:
			info['starred'] = starred.date.isoformat()

		rating = Store.of(self).get(RatingTrack, (user.id, self.id))
		if rating:
			info['userRating'] = rating.rating
		avgRating = Store.of(self).find(RatingTrack, RatingTrack.rated_id == self.id).avg(RatingTrack.rating)
		if avgRating:
			info['averageRating'] = avgRating

		if prefs and prefs.format and prefs.format != self.suffix():
			info['transcodedSuffix'] = prefs.format
			info['transcodedContentType'] = config.get_mime(prefs.format)

		return info

	def duration_str(self):
		ret = '%02i:%02i' % ((self.duration % 3600) / 60, self.duration % 60)
		if self.duration >= 3600:
			ret = '%02i:%s' % (self.duration / 3600, ret)
		return ret

	def suffix(self):
		return os.path.splitext(self.path)[1][1:].lower()

	def sort_key(self):
		return (self.album.artist.name + self.album.name + ("%02i" % self.disc) + ("%02i" % self.number) + self.title).lower()

Folder.tracks = ReferenceSet(Folder.id, Track.folder_id)
Album.tracks =  ReferenceSet(Album.id,  Track.album_id)
Artist.tracks = ReferenceSet(Artist.id, Track.artist_id)

class User(object):
	__storm_table__ = 'user'

	id = UUID(primary = True, default_factory = uuid.uuid4)
	name = Unicode() # unique
	mail = Unicode()
	password = Unicode()
	salt = Unicode()
	admin = Bool(default = False)
	lastfm_session = Unicode() # nullable
	lastfm_status = Bool(default = True) # True: ok/unlinked, False: invalid session

	last_play_id = UUID() # nullable
	last_play = Reference(last_play_id, Track.id)
	last_play_date = DateTime() # nullable

	def as_subsonic_user(self):
		return {
			'username': self.name,
			'email': self.mail,
			'scrobblingEnabled': self.lastfm_session is not None and self.lastfm_status,
			'adminRole': self.admin,
			'settingsRole': True,
			'downloadRole': True,
			'uploadRole': False,
			'playlistRole': True,
			'coverArtRole': False,
			'commentRole': False,
			'podcastRole': False,
			'streamRole': True,
			'jukeboxRole': False,
			'shareRole': False
		}

class ClientPrefs(object):
	__storm_table__ = 'client_prefs'
	__storm_primary__ = 'user_id', 'client_name'

	user_id = UUID()
	client_name = Unicode()
	format = Unicode() # nullable
	bitrate = Int() # nullable

class BaseStarred(object):
	__storm_primary__ = 'user_id', 'starred_id'

	user_id = UUID()
	starred_id = UUID()
	date = DateTime(default_factory = now)

	user = Reference(user_id, User.id)

class StarredFolder(BaseStarred):
	__storm_table__ = 'starred_folder'

	starred = Reference(BaseStarred.starred_id, Folder.id)

class StarredArtist(BaseStarred):
	__storm_table__ = 'starred_artist'

	starred = Reference(BaseStarred.starred_id, Artist.id)

class StarredAlbum(BaseStarred):
	__storm_table__ = 'starred_album'

	starred = Reference(BaseStarred.starred_id, Album.id)

class StarredTrack(BaseStarred):
	__storm_table__ = 'starred_track'

	starred = Reference(BaseStarred.starred_id, Track.id)

class BaseRating(object):
	__storm_primary__ = 'user_id', 'rated_id'

	user_id = UUID()
	rated_id = UUID()
	rating = Int()

	user = Reference(user_id, User.id)

class RatingFolder(BaseRating):
	__storm_table__ = 'rating_folder'

	rated = Reference(BaseRating.rated_id, Folder.id)

class RatingTrack(BaseRating):
	__storm_table__ = 'rating_track'

	rated = Reference(BaseRating.rated_id, Track.id)

class ChatMessage(object):
	__storm_table__ = 'chat_message'

	id = UUID(primary = True, default_factory = uuid.uuid4)
	user_id = UUID()
	time = Int(default_factory = lambda: int(time.time()))
	message = Unicode()

	user = Reference(user_id, User.id)

	def responsize(self):
		return {
			'username': self.user.name,
			'time': self.time * 1000,
			'message': self.message
		}

class Playlist(object):
	__storm_table__ = 'playlist'

	id = UUID(primary = True, default_factory = uuid.uuid4)
	user_id = UUID()
	name = Unicode()
	comment = Unicode() # nullable
	public = Bool(default = False)
	created = DateTime(default_factory = now)

	user = Reference(user_id, User.id)

	def as_subsonic_playlist(self, user):
		info = {
			'id': str(self.id),
			'name': self.name if self.user_id == user.id else '[%s] %s' % (self.user.name, self.name),
			'owner': self.user.name,
			'public': self.public,
			'songCount': self.tracks.count(),
			'duration': self.tracks.find().sum(Track.duration),
			'created': self.created.isoformat()
		}
		if self.comment:
			info['comment'] = self.comment
		return info

class PlaylistTrack(object):
	__storm_table__ = 'playlist_track'
	__storm_primary__ = 'playlist_id', 'track_id'

	playlist_id = UUID()
	track_id = UUID()

Playlist.tracks = ReferenceSet(Playlist.id, PlaylistTrack.playlist_id, PlaylistTrack.track_id, Track.id)

def get_store(database_uri):
	database = create_database(database_uri)
	store = Store(database)
	return store


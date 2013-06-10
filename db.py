# coding: utf-8

import config

from sqlalchemy import create_engine, Column, ForeignKey
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.types import TypeDecorator
from sqlalchemy.types import BINARY

import uuid, datetime
import os.path
 
class UUID(TypeDecorator):
	impl = BINARY

	def __init__(self):
		self.impl.length = 16
		TypeDecorator.__init__(self, length = self.impl.length)

	def process_bind_param(self, value, dialect = None):
		if value and isinstance(value, uuid.UUID):
			return value.bytes
		if value and not isinstance(value, uuid.UUID):
			raise ValueError, 'value %s is not a valid uuid.UUID' % value
		return None

	def process_result_value(self, value, dialect = None):
		if value:
			return uuid.UUID(bytes = value)
		return None

	def is_mutable(self):
		return False

	@staticmethod
	def gen_id_column():
		return Column(UUID, primary_key = True, default = uuid.uuid4)

def now():
	return datetime.datetime.now().replace(microsecond = 0)

engine = create_engine(config.get('DATABASE_URI'), convert_unicode = True)
session = scoped_session(sessionmaker(autocommit = False, autoflush = False, bind = engine))

Base = declarative_base()
Base.query = session.query_property()

class User(Base):
	__tablename__ = 'user'

	id = UUID.gen_id_column()
	name = Column(String, unique = True)
	mail = Column(String)
	password = Column(String(40))
	salt = Column(String(6))
	admin = Column(Boolean, default = False)
	lastfm_session = Column(String(32), nullable = True)
	lastfm_status = Column(Boolean, default = True) # True: ok/unlinked, False: invalid session

	last_play_id = Column(UUID, ForeignKey('track.id'), nullable = True)
	last_play = relationship('Track')
	last_play_date = Column(DateTime, nullable = True)

class Folder(Base):
	__tablename__ = 'folder'

	id = UUID.gen_id_column()
	root = Column(Boolean, default = False)
	name = Column(String)
	path = Column(String, unique = True)
	created = Column(DateTime, default = now)
	has_cover_art = Column(Boolean, default = False)
	last_scan = Column(DateTime, default = datetime.datetime.min)

	parent_id = Column(UUID, ForeignKey('folder.id'), nullable = True)
	children = relationship('Folder', backref = backref('parent', remote_side = [ id ]))

	def as_subsonic_child(self):
		info = {
			'id': str(self.id),
			'isDir': True,
			'title': self.name,
			'created': self.created.isoformat()
		}
		if not self.root:
			info['parent'] = str(self.parent_id)
			info['artist'] = self.parent.name
		if self.has_cover_art:
			info['coverArt'] = str(self.id)

		return info

class Artist(Base):
	__tablename__ = 'artist'

	id = UUID.gen_id_column()
	name = Column(String, unique = True)
	albums = relationship('Album', backref = 'artist')

	def as_subsonic_artist(self):
		return {
			'id': str(self.id),
			'name': self.name,
			# coverArt
			'albumCount': len(self.albums)
			# starred
		}

class Album(Base):
	__tablename__ = 'album'

	id = UUID.gen_id_column()
	name = Column(String)
	artist_id = Column(UUID, ForeignKey('artist.id'))
	tracks = relationship('Track', backref = 'album')

	def as_subsonic_album(self):
		info = {
			'id': str(self.id),
			'name': self.name,
			'artist': self.artist.name,
			'artistId': str(self.artist_id),
			'songCount': len(self.tracks),
			'duration': sum(map(lambda t: t.duration, self.tracks)),
			'created': min(map(lambda t: t.created, self.tracks)).isoformat()
			# starred
		}
		if self.tracks[0].folder.has_cover_art:
			info['coverArt'] = str(self.tracks[0].folder_id)

		return info

	def sort_key(self):
		year = min(map(lambda t: t.year if t.year else 9999, self.tracks))
		return '%i%s' % (year, self.name.lower())

class Track(Base):
	__tablename__ = 'track'

	id = UUID.gen_id_column()
	disc = Column(Integer)
	number = Column(Integer)
	title = Column(String)
	year = Column(Integer, nullable = True)
	genre = Column(String, nullable = True)
	duration = Column(Integer)
	album_id = Column(UUID, ForeignKey('album.id'))
	bitrate = Column(Integer)

	path = Column(String, unique = True)
	created = Column(DateTime, default = now)
	last_modification = Column(Integer)

	play_count = Column(Integer, default = 0)
	last_play = Column(DateTime, nullable = True)

	root_folder_id = Column(UUID, ForeignKey('folder.id'))
	root_folder = relationship('Folder', primaryjoin = Folder.id == root_folder_id)
	folder_id = Column(UUID, ForeignKey('folder.id'))
	folder = relationship('Folder', primaryjoin = Folder.id == folder_id, backref = 'tracks')

	def as_subsonic_child(self):
		info = {
			'id': str(self.id),
			'parent': str(self.folder.id),
			'isDir': False,
			'title': self.title,
			'album': self.album.name,
			'artist': self.album.artist.name,
			'track': self.number,
			'size': os.path.getsize(self.path),
			'contentType': 'audio/mpeg', # we only know how to read mp3s
			'suffix': 'mp3', # same as above
			'duration': self.duration,
			'bitRate': self.bitrate,
			'path': self.path[len(self.root_folder.path) + 1:],
			'isVideo': False,
			'discNumber': self.disc,
			'created': self.created.isoformat(),
			'albumId': str(self.album.id),
			'artistId': str(self.album.artist.id),
			'type': 'music'
		}

		if self.year:
			info['year'] = self.year
		if self.genre:
			info['genre'] = self.genre
		if self.folder.has_cover_art:
			info['coverArt'] = str(self.folder_id)

		# transcodedContentType
		# transcodedSuffix
		# userRating
		# averageRating
		# starred

		return info

	def duration_str(self):
		ret = '%02i:%02i' % ((self.duration % 3600) / 60, self.duration % 60)
		if self.duration >= 3600:
			ret = '%02i:%s' % (self.duration / 3600, ret)
		return ret

	def sort_key(self):
		return (self.album.artist.name + self.album.name + ("%02i" % self.disc) + ("%02i" % self.number) + self.title).lower()

def init_db():
	Base.metadata.create_all(bind = engine)

def recreate_db():
	Base.metadata.drop_all(bind = engine)
	Base.metadata.create_all(bind = engine)


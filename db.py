# coding: utf-8

import config

from sqlalchemy import create_engine, Column, ForeignKey
from sqlalchemy import Integer, String, Boolean, DateTime
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.types import TypeDecorator
from sqlalchemy import BINARY

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
	admin = Column(Boolean)

class Folder(Base):
	__tablename__ = 'folder'

	id = UUID.gen_id_column()
	root = Column(Boolean, default = False)
	name = Column(String)
	path = Column(String, unique = True)
	last_scan = Column(DateTime, default = datetime.datetime.min)

	parent_id = Column(UUID, ForeignKey('folder.id'), nullable = True)
	children = relationship('Folder', backref = backref('parent', remote_side = [ id ]))

class Artist(Base):
	__tablename__ = 'artist'

	id = UUID.gen_id_column()
	name = Column(String, unique = True)
	albums = relationship('Album', backref = 'artist')

class Album(Base):
	__tablename__ = 'album'

	id = UUID.gen_id_column()
	name = Column(String)
	artist_id = Column(UUID, ForeignKey('artist.id'))
	tracks = relationship('Track', backref = 'album')

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
	path = Column(String, unique = True)
	bitrate = Column(Integer)

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
			'albumId': str(self.album.id),
			'artistId': str(self.album.artist.id),
			'type': 'music'
		}

		if self.year:
			info['year'] = self.year
		if self.genre:
			info['genre'] = self.genre

		# coverArt
		# transcodedContentType
		# transcodedSuffix
		# userRating
		# averageRating
		# created
		# starred

		return info

	def duration_str(self):
		ret = '%02i:%02i' % ((self.duration % 3600) / 60, self.duration % 60)
		if self.duration >= 3600:
			ret = '%02i:%s' % (self.duration / 3600, ret)
		return ret

def init_db():
	Base.metadata.create_all(bind = engine)

def recreate_db():
	Base.metadata.drop_all(bind = engine)
	Base.metadata.create_all(bind = engine)


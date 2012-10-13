# coding: utf-8

import config

from sqlalchemy import create_engine, Column, ForeignKey
from sqlalchemy import Integer, String, Boolean, Date, Time
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.types import TypeDecorator
from sqlalchemy import BINARY

import uuid
 
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

class MusicFolder(Base):
	__tablename__ = 'folder'

	id = UUID.gen_id_column()
	name = Column(String, unique = True)
	path = Column(String)
	last_scan = Column(Date, nullable = True)

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
	duration = Column(Time)
	album_id = Column(UUID, ForeignKey('album.id'))
	path = Column(String, unique = True)

def init_db():
	Base.metadata.create_all(bind = engine)

def recreate_db():
	Base.metadata.drop_all(bind = engine)
	Base.metadata.create_all(bind = engine)


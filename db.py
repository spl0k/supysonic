# coding: utf-8

import config
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy import types
from sqlalchemy import BINARY
from sqlalchemy.schema import Column
import uuid
 
class UUID(types.TypeDecorator):
	impl = BINARY
	def __init__(self):
		self.impl.length = 16
		types.TypeDecorator.__init__(self, length = self.impl.length)

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
db_session = scoped_session(sessionmaker(autocommit = False, autoflush = False, bind = engine))

Base = declarative_base()
Base.query = db_session.query_property()

class User(Base):
	__tablename__ = 'users'

	id = UUID.gen_id_column()
	name = Column(String, unique = True)
	mail = Column(String)
	password = Column(String(40))
	salt = Column(String(6))
	admin = Column(Boolean)

class MusicFolder(Base):
	__tablename__ = 'folders'

	id = UUID.gen_id_column()
	name = Column(String, unique = True)
	path = Column(String)

def init_db():
	Base.metadata.drop_all(bind = engine)
	Base.metadata.create_all(bind = engine)


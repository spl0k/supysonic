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

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.types import TypeDecorator
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.dialects.postgresql import UUID as pgUUID

import uuid
import datetime
import time
import mimetypes
import os.path

import sqlamp

from web import app

database = SQLAlchemy(app)
session = database.session

Column = database.Column
Table = database.Table
Unicode = database.Unicode
ForeignKey = database.ForeignKey
func = database.func
Integer = database.Integer
Boolean = database.Boolean
DateTime = database.DateTime
relationship = database.relationship
backref = database.backref
BINARY = database.BINARY


class UnicodeMixIn(object):

    __table_args__ = {'mysql_charset': 'utf8'}

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

metadata = database.MetaData(database.engine)
Base = declarative_base(metadata=metadata, metaclass=sqlamp.DeclarativeMeta)


class UUID(TypeDecorator):
    """Platform-somewhat-independent UUID type

    Uses Postgresql's UUID type, otherwise uses BINARY(16),
    should be more efficient than a CHAR(32).

    Mix of http://stackoverflow.com/a/812363
    and http://www.sqlalchemy.org/docs/core/types.html#backend-agnostic-guid-type
    """

    impl = BINARY

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(pgUUID())
        else:
            return dialect.type_descriptor(BINARY(16))

    def process_bind_param(self, value, dialect):
        if value and isinstance(value, uuid.UUID):
            if dialect.name == 'postgresql':
                return value
            return value.bytes
        if value and isinstance(value, basestring):
            return uuid.UUID(value).bytes
        elif value:
            raise ValueError, 'value %s is not a valid uuid.UUID' % value
        return None

    def process_result_value(self, value, dialect):
        if value:
            if dialect.name == 'postgresql':
                return uuid.UUID(value)
            return uuid.UUID(bytes = value)
        return None

    def is_mutable(self):
        return False

    @staticmethod
    def gen_id_column():
        return Column(UUID, primary_key = True, default = uuid.uuid4)


def now():
    return datetime.datetime.now().replace(microsecond = 0)


class User(Base, UnicodeMixIn):

    id = UUID.gen_id_column()
    name = Column(Unicode(64), unique = True)
    mail = Column(Unicode(255))
    password = Column(BINARY(20))
    admin = Column(Boolean, default = False)
    lastfm_session = Column(Unicode(32), nullable = True)
    lastfm_status = Column(Boolean, default = True) # True: ok/unlinked, False: invalid session

    last_play_id = Column(UUID, ForeignKey('track.id', ondelete = 'SET NULL'), nullable = True)
    last_play = relationship('Track')
    last_play_date = Column(DateTime, nullable = True)

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


class ClientPrefs(Base, UnicodeMixIn):

    user_id = Column(UUID, ForeignKey('user.id'), primary_key = True)
    client_name = Column(Unicode(32), nullable = False, primary_key = True)
    format = Column(Unicode(8), nullable = True)
    bitrate = Column(Integer, nullable = True)


class Folder(Base, UnicodeMixIn):
    __tablename__ = 'folder'
    __mp_manager__ = 'mp'

    id = UUID.gen_id_column()
    root = Column(Boolean, default = False)
    path = Column(Unicode(4096)) # should be unique, but mysql don't like such large columns
    created = Column(DateTime, default = now)
    last_scan = Column(DateTime, default = now)

    parent_id = Column(ForeignKey('folder.id', ondelete="CASCADE"))
    parent = relationship("Folder", remote_side=[id])

    @hybrid_property
    def name(self):
        return os.path.basename(self.path)


    def get_children(self):
        return self.mp.query_children().all()

    def as_subsonic_child(self, user):

        info = {
            'id': self.id,
            'isDir': True,
            'title': self.name,
            'album': self.name,
            'created': self.created.isoformat()
        }

        if not self.root and self.parent:
            info['parent'] = self.parent.id
            info['artist'] = self.parent.name

        info['coverArt'] = self.id

        starred = session.query(StarredFolder).get((user.id, self.id))
        if starred:
            info['starred'] = starred.date.isoformat()

        rating = session.query(RatingFolder).get((user.id, self.id))
        if rating:
            info['userRating'] = rating.rating
            avgRating = session.query(RatingFolder).filter(RatingFolder.rated_id == self.id).value(func.avg(RatingFolder.rating))
            if avgRating:
                info['averageRating'] = avgRating

        return info


class Album(Base, UnicodeMixIn):

    id = UUID.gen_id_column()
    name = Column(Unicode(255))
    artist_id = Column(UUID, ForeignKey('artist.id'))
    year = Column(Unicode(32))

    def as_subsonic_album(self, user):
        info = {
            'id': self.id,
            'name': self.name,
            'artist': self.artist.name,
            'artistId': self.artist_id,
            'songCount': len(self.tracks),
            'duration': sum(map(lambda t: t.duration, self.tracks)),
            'created': min(map(lambda t: t.created, self.tracks)).isoformat(),
            'year': self.year
        }

        if self.tracks:
            info['coverArt'] = self.tracks[0].folder.id

        starred = session.query(StarredAlbum).get((user.id, self.id))
        if starred:
            info['starred'] = starred.date.isoformat()

        return info

    def sort_key(self):
        year = min(map(lambda t: t.year if t.year else 9999, self.tracks))
        return '%i%s' % (year, self.name.lower())


class Artist(Base, UnicodeMixIn):

    id = UUID.gen_id_column()
    name = Column(Unicode(255), nullable=False)
    albums = relationship(Album, backref = 'artist')

    def as_subsonic_artist(self, user):
        info = {
            'id': self.id,
            'name': self.name,
            # coverArt
            'albumCount': len(self.albums)
        }

        starred = session.query(StarredArtist).get((user.id, self.id))
        if starred:
            info['starred'] = starred.date.isoformat()

        return info


class Track(Base, UnicodeMixIn):

    id = UUID.gen_id_column()
    disc = Column(Integer)
    number = Column(Integer)
    title = Column(Unicode(255))
    artist = Column(Unicode(255))
    year = Column(Integer, nullable = True)
    genre = Column(Unicode(255), nullable = True)
    duration = Column(Integer)
    bitrate = Column(Integer)

    path = Column(Unicode(4096)) # should be unique, but mysql don't like such large columns
    created = Column(DateTime, default = now)
    last_modification = Column(Integer)

    play_count = Column(Integer, default = 0)
    last_play = Column(DateTime, nullable = True)

    folder_id = Column(UUID, ForeignKey('folder.id'))
    folder = relationship('Folder', backref = backref('tracks', cascade="save-update, delete"))

    album_id = Column(UUID, ForeignKey('album.id'))
    album = relationship(Album, backref = backref('tracks', cascade="save-update, delete"))

    def as_subsonic_child(self, user):
        if (os.path.isfile(self.path)):
            size = os.path.getsize(self.path)
        else:
            size = 0
        info = {
            'id': self.id,
            'parent': self.folder.id,
            'isDir': False,
            'title': self.title,
            'album': self.album.name,
            'artist': self.artist,
            'track': self.number,
            'size': size,
            'contentType': mimetypes.guess_type(self.path),
            'suffix': self.suffix(),
            'duration': self.duration,
            'bitRate': self.bitrate,
            'path': self.path,
            'isVideo': False,
            'discNumber': self.disc,
            'created': self.created.isoformat(),
            'albumId': self.album.id,
            'artistId': self.album.artist.id,
            'type': 'music'
        }

        if self.year:
            info['year'] = self.year

        if self.genre:
            info['genre'] = self.genre

        info['coverArt'] = self.folder.id

        starred = session.query(StarredTrack).get((user.id, self.id))
        if starred:
            info['starred'] = starred.date.isoformat()

        rating = session.query(RatingTrack).get((user.id, self.id))
        if rating:
            info['userRating'] = rating.rating
            avgRating = session.query(RatingTrack).filter(RatingTrack.rated_id == self.id).value(func.avg(RatingTrack.rating))
            if avgRating:
                info['averageRating'] = avgRating

        if self.suffix() == 'flac':
            info['transcodedContentType'] = 'audio/ogg'
            info['transcodedSuffix'] = 'ogg'

        return info

    def duration_str(self):
        ret = '%02i:%02i' % ((self.duration % 3600) / 60, self.duration % 60)
        if self.duration >= 3600:
            ret = '%02i:%s' % (self.duration / 3600, ret)
            return ret

    def suffix(self):
        return os.path.splitext(self.path)[1][1:].lower()

    def sort_key(self):
        #return (self.album.artist.name + self.album.name + ("%02i" % self.disc) + ("%02i" % self.number) + self.title).lower()
        return (self.album.name + ("%02i" % self.disc) + ("%02i" % self.number) + self.title).lower()


class StarredFolder(Base, UnicodeMixIn):

    user_id = Column(UUID, ForeignKey('user.id'), primary_key = True)
    starred_id = Column(UUID, ForeignKey('folder.id'), primary_key = True)
    date = Column(DateTime, default = now)

    user = relationship('User')
    starred = relationship('Folder')


class StarredArtist(Base, UnicodeMixIn):

    user_id = Column(UUID, ForeignKey('user.id'), primary_key = True)
    starred_id = Column(UUID, ForeignKey('artist.id'), primary_key = True)
    date = Column(DateTime, default = now)

    user = relationship('User')
    starred = relationship('Artist')


class StarredAlbum(Base, UnicodeMixIn):

    user_id = Column(UUID, ForeignKey('user.id'), primary_key = True)
    starred_id = Column(UUID, ForeignKey('album.id'), primary_key = True)
    date = Column(DateTime, default = now)

    user = relationship('User')
    starred = relationship('Album')


class StarredTrack(Base, UnicodeMixIn):

    user_id = Column(UUID, ForeignKey('user.id'), primary_key = True)
    starred_id = Column(UUID, ForeignKey('track.id'), primary_key = True)
    date = Column(DateTime, default = now)

    user = relationship('User')
    starred = relationship('Track')


class RatingFolder(Base, UnicodeMixIn):

    user_id = Column(UUID, ForeignKey('user.id'), primary_key = True)
    rated_id = Column(UUID, ForeignKey('folder.id'), primary_key = True)
    rating = Column(Integer)

    user = relationship('User')
    rated = relationship('Folder')


class RatingTrack(Base, UnicodeMixIn):

    user_id = Column(UUID, ForeignKey('user.id'), primary_key = True)
    rated_id = Column(UUID, ForeignKey('track.id'), primary_key = True)
    rating = Column(Integer)

    user = relationship('User')
    rated = relationship('Track')


class ChatMessage(Base, UnicodeMixIn):

    id = UUID.gen_id_column()
    user_id = Column(UUID, ForeignKey('user.id'))
    time = Column(Integer, default = lambda: int(time.time()))
    message = Column(Unicode(512))

    user = relationship('User')

    def responsize(self):
        return {
            'username': self.user.name,
            'time': self.time * 1000,
            'message': self.message
        }


playlist_track_assoc = Table('playlist_track', Base.metadata,
                             Column('playlist_id', UUID, ForeignKey('playlist.id')),
                             Column('track_id', UUID, ForeignKey('track.id'))
                             )

class Playlist(Base, UnicodeMixIn):

    id = UUID.gen_id_column()
    user_id = Column(UUID, ForeignKey('user.id'))
    name = Column(Unicode(255))
    comment = Column(Unicode(255), nullable = True)
    public = Column(Boolean, default = False)
    created = Column(DateTime, default = now)

    user = relationship('User')
    tracks = relationship('Track', secondary = playlist_track_assoc)

    def as_subsonic_playlist(self, user):
        info = {
            'id': self.id,
            'name': self.name if self.user_id == user.id else '[%s] %s' % (self.user.name, self.name),
            'owner': self.user.name,
            'public': self.public,
            'songCount': len(self.tracks),
            'duration': sum(map(lambda t: t.duration, self.tracks)),
            'created': self.created.isoformat()
        }
        if self.comment:
            info['comment'] = self.comment
            return info


def recreate_db():
    metadata.drop_all()
    metadata.create_all()

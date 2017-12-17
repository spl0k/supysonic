# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2017  Alban 'spl0k' Féron
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

import time
import mimetypes
import os.path

from datetime import datetime
from pony.orm import Database, Required, Optional, Set, PrimaryKey
from pony.orm import ObjectNotFound
from pony.orm import min, max, avg, sum
from urlparse import urlparse
from uuid import UUID, uuid4

def now():
    return datetime.now().replace(microsecond = 0)

db = Database()

class Folder(db.Entity):
    _table_ = 'folder'

    id = PrimaryKey(UUID, default = uuid4)
    root = Required(bool, default = False)
    name = Required(str)
    path = Required(str, unique = True)
    created = Required(datetime, precision = 0, default = now)
    has_cover_art = Required(bool, default = False)
    last_scan = Required(int, default = 0)

    parent = Optional(lambda: Folder, reverse = 'children', column = 'parent_id')
    children = Set(lambda: Folder, reverse = 'parent')

    __alltracks = Set(lambda: Track, lazy = True, reverse = 'root_folder') # Never used, hide it. Could be huge, lazy load
    tracks = Set(lambda: Track, reverse = 'folder')

    stars = Set(lambda: StarredFolder)
    ratings = Set(lambda: RatingFolder)

    def as_subsonic_child(self, user):
        info = {
            'id': str(self.id),
            'isDir': True,
            'title': self.name,
            'album': self.name,
            'created': self.created.isoformat()
        }
        if not self.root:
            info['parent'] = str(self.parent.id)
            info['artist'] = self.parent.name
        if self.has_cover_art:
            info['coverArt'] = str(self.id)

        try:
            starred = StarredFolder[user.id, self.id]
            info['starred'] = starred.date.isoformat()
        except ObjectNotFound: pass

        try:
            rating = RatingFolder[user.id, self.id]
            info['userRating'] = rating.rating
        except ObjectNotFound: pass

        avgRating = avg(self.ratings.rating)
        if avgRating:
            info['averageRating'] = avgRating

        return info

class Artist(db.Entity):
    _table_ = 'artist'

    id = PrimaryKey(UUID, default = uuid4)
    name = Required(str, unique = True)
    albums = Set(lambda: Album)
    tracks = Set(lambda: Track)

    stars = Set(lambda: StarredArtist)

    def as_subsonic_artist(self, user):
        info = {
            'id': str(self.id),
            'name': self.name,
            # coverArt
            'albumCount': self.albums.count()
        }

        try:
            starred = StarredArtist[user.id, self.id]
            info['starred'] = starred.date.isoformat()
        except ObjectNotFound: pass

        return info

class Album(db.Entity):
    _table_ = 'album'

    id = PrimaryKey(UUID, default = uuid4)
    name = Required(str)
    artist = Required(Artist, column = 'artist_id')
    tracks = Set(lambda: Track)

    stars = Set(lambda: StarredAlbum)

    def as_subsonic_album(self, user):
        info = {
            'id': str(self.id),
            'name': self.name,
            'artist': self.artist.name,
            'artistId': str(self.artist.id),
            'songCount': self.tracks.count(),
            'duration': sum(self.tracks.duration),
            'created': min(self.tracks.created).isoformat()
        }

        track_with_cover = self.tracks.select(lambda t: t.folder.has_cover_art)[:1][0]
        if track_with_cover:
            info['coverArt'] = str(track_with_cover.folder.id)

        try:
            starred = StarredAlbum[user.id, self.id]
            info['starred'] = starred.date.isoformat()
        except ObjectNotFound: pass

        return info

    def sort_key(self):
        year = min(map(lambda t: t.year if t.year else 9999, self.tracks))
        return '%i%s' % (year, self.name.lower())

class Track(db.Entity):
    _table_ = 'track'

    id = PrimaryKey(UUID, default = uuid4)
    disc = Required(int)
    number = Required(int)
    title = Required(str)
    year = Optional(int)
    genre = Optional(str, nullable = True)
    duration = Required(int)

    album = Required(Album, column = 'album_id')
    artist = Required(Artist, column = 'artist_id')

    bitrate = Required(int)

    path = Required(str, unique = True)
    content_type = Required(str)
    created = Required(datetime, precision = 0, default = now)
    last_modification = Required(int)

    play_count = Required(int, default = 0)
    last_play = Optional(datetime, precision = 0)

    root_folder = Required(Folder, column = 'root_folder_id')
    folder = Required(Folder, column = 'folder_id')

    __lastly_played_by = Set(lambda: User) # Never used, hide it

    stars = Set(lambda: StarredTrack)
    ratings = Set(lambda: RatingTrack)

    def as_subsonic_child(self, user, prefs):
        info = {
            'id': str(self.id),
            'parent': str(self.folder.id),
            'isDir': False,
            'title': self.title,
            'album': self.album.name,
            'artist': self.artist.name,
            'track': self.number,
            'size': os.path.getsize(self.path) if os.path.isfile(self.path) else -1,
            'contentType': self.content_type,
            'suffix': self.suffix(),
            'duration': self.duration,
            'bitRate': self.bitrate,
            'path': self.path[len(self.root_folder.path) + 1:],
            'isVideo': False,
            'discNumber': self.disc,
            'created': self.created.isoformat(),
            'albumId': str(self.album.id),
            'artistId': str(self.artist.id),
            'type': 'music'
        }

        if self.year:
            info['year'] = self.year
        if self.genre:
            info['genre'] = self.genre
        if self.folder.has_cover_art:
            info['coverArt'] = str(self.folder.id)

        try:
            starred = StarredTrack[user.id, self.id]
            info['starred'] = starred.date.isoformat()
        except ObjectNotFound: pass

        try:
            rating = RatingTrack[user.id, self.id]
            info['userRating'] = rating.rating
        except ObjectNotFound: pass

        avgRating = avg(self.ratings.rating)
        if avgRating:
            info['averageRating'] = avgRating

        if prefs and prefs.format and prefs.format != self.suffix():
            info['transcodedSuffix'] = prefs.format
            info['transcodedContentType'] = mimetypes.guess_type('dummyname.' + prefs.format, False)[0] or 'application/octet-stream'

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

class User(db.Entity):
    _table_ = 'user'

    id = PrimaryKey(UUID, default = uuid4)
    name = Required(str, unique = True)
    mail = Optional(str)
    password = Required(str)
    salt = Required(str)
    admin = Required(bool, default = False)
    lastfm_session = Optional(str)
    lastfm_status = Required(bool, default = True) # True: ok/unlinked, False: invalid session

    last_play = Optional(Track, column = 'last_play_id')
    last_play_date = Optional(datetime, precision = 0)

    clients = Set(lambda: ClientPrefs)
    playlists = Set(lambda: Playlist)
    __messages = Set(lambda: ChatMessage, lazy = True) # Never used, hide it

    starred_folders = Set(lambda: StarredFolder, lazy = True)
    starred_artists = Set(lambda: StarredArtist, lazy = True)
    starred_albums =  Set(lambda: StarredAlbum,  lazy = True)
    starred_tracks =  Set(lambda: StarredTrack,  lazy = True)
    folder_ratings =  Set(lambda: RatingFolder,  lazy = True)
    track_ratings =   Set(lambda: RatingTrack,   lazy = True)

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

class ClientPrefs(db.Entity):
    _table_ = 'client_prefs'

    user = Required(User, column = 'user_id')
    client_name = Required(str)
    PrimaryKey(user, client_name)
    format = Optional(str)
    bitrate = Optional(int)

class StarredFolder(db.Entity):
    _table_ = 'starred_folder'

    user = Required(User, column = 'user_id')
    starred = Required(Folder, column = 'starred_id')
    date = Required(datetime, precision = 0, default = now)

    PrimaryKey(user, starred)

class StarredArtist(db.Entity):
    _table_ = 'starred_artist'

    user = Required(User, column = 'user_id')
    starred = Required(Artist, column = 'starred_id')
    date = Required(datetime, precision = 0, default = now)

    PrimaryKey(user, starred)

class StarredAlbum(db.Entity):
    _table_ = 'starred_album'

    user = Required(User, column = 'user_id')
    starred = Required(Album, column = 'starred_id')
    date = Required(datetime, precision = 0, default = now)

    PrimaryKey(user, starred)

class StarredTrack(db.Entity):
    _table_ = 'starred_track'

    user = Required(User, column = 'user_id')
    starred = Required(Track, column = 'starred_id')
    date = Required(datetime, precision = 0, default = now)

    PrimaryKey(user, starred)

class RatingFolder(db.Entity):
    _table_ = 'rating_folder'
    user = Required(User, column = 'user_id')
    rated = Required(Folder, column = 'rated_id')
    rating = Required(int)

    PrimaryKey(user, rated)

class RatingTrack(db.Entity):
    _table_ = 'rating_track'
    user = Required(User, column = 'user_id')
    rated = Required(Track, column = 'rated_id')
    rating = Required(int)

    PrimaryKey(user, rated)

class ChatMessage(db.Entity):
    _table_ = 'chat_message'

    id = PrimaryKey(UUID, default = uuid4)
    user = Required(User, column = 'user_id')
    time = Required(int, default = lambda: int(time.time()))
    message = Required(str)

    def responsize(self):
        return {
            'username': self.user.name,
            'time': self.time * 1000,
            'message': self.message
        }

class Playlist(db.Entity):
    _table_ = 'playlist'

    id = PrimaryKey(UUID, default = uuid4)
    user = Required(User, column = 'user_id')
    name = Required(str)
    comment = Optional(str)
    public = Required(bool, default = False)
    created = Required(datetime, precision = 0, default = now)
    tracks = Optional(str)

    def as_subsonic_playlist(self, user):
        tracks = self.get_tracks()
        info = {
            'id': str(self.id),
            'name': self.name if self.user.id == user.id else '[%s] %s' % (self.user.name, self.name),
            'owner': self.user.name,
            'public': self.public,
            'songCount': len(tracks),
            'duration': sum(map(lambda t: t.duration, tracks)),
            'created': self.created.isoformat()
        }
        if self.comment:
            info['comment'] = self.comment
        return info

    def get_tracks(self):
        if not self.tracks:
            return []

        tracks = []
        should_fix = False

        for t in self.tracks.split(','):
            try:
                tid = UUID(t)
                track = Track[tid]
                tracks.append(track)
            except:
                should_fix = True

        if should_fix:
            self.tracks = ','.join(map(lambda t: str(t.id), tracks))
            db.commit()

        return tracks

    def clear(self):
        self.tracks = ''

    def add(self, track):
        if isinstance(track, UUID):
            tid = track
        elif isinstance(track, Track):
            tid = track.id
        elif isinstance(track, basestring):
            tid = UUID(track)

        if self.tracks and len(self.tracks) > 0:
            self.tracks = '{},{}'.format(self.tracks, tid)
        else:
            self.tracks = str(tid)

    def remove_at_indexes(self, indexes):
        tracks = self.tracks.split(',')
        for i in indexes:
            if i < 0 or i >= len(tracks):
                continue
            tracks[i] = None

        self.tracks = ','.join(t for t in tracks if t)

def parse_uri(database_uri):
    if not isinstance(database_uri, basestring):
        raise TypeError('Expecting a string')

    uri = urlparse(database_uri)
    if uri.scheme == 'sqlite':
        path = uri.path
        if not path:
            path = ':memory:'
        elif path[0] == '/':
            path = path[1:]

        return dict(provider = 'sqlite', filename = path)
    elif uri.scheme in ('postgres', 'postgresql'):
        return dict(provider = 'postgres', user = uri.username, password = uri.password, host = uri.hostname, database = uri.path[1:])
    elif uri.scheme == 'mysql':
        return dict(provider = 'mysql', user = uri.username, passwd = uri.password, host = uri.hostname, db = uri.path[1:])
    return dict()

def get_database(database_uri, create_tables = False):
    db.bind(**parse_uri(database_uri))
    db.generate_mapping(create_tables = create_tables)
    return db

def release_database(db):
    if not isinstance(db, Database):
        raise TypeError('Expecting a pony.orm.Database instance')

    db.disconnect()
    db.provider = None
    db.schema = None


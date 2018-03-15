# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import time
import mimetypes
import os.path

from datetime import datetime
from pony.orm import Database, Required, Optional, Set, PrimaryKey, LongStr
from pony.orm import ObjectNotFound
from pony.orm import min, max, avg, sum, exists
from uuid import UUID, uuid4

from .py23 import dict, strtype

try:
    from urllib.parse import urlparse, parse_qsl
except ImportError:
    from urlparse import urlparse, parse_qsl

def now():
    return datetime.now().replace(microsecond = 0)

db = Database()

class Folder(db.Entity):
    _table_ = 'folder'

    id = PrimaryKey(UUID, default = uuid4)
    root = Required(bool, default = False)
    name = Required(str)
    path = Required(str, 4096) # unique
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
        info = dict(
            id = str(self.id),
            isDir = True,
            title = self.name,
            album = self.name,
            created = self.created.isoformat()
        )
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

    @classmethod
    def prune(cls):
        query = cls.select(lambda self: not exists(t for t in Track if t.folder == self) and \
            not exists(f for f in Folder if f.parent == self) and not self.root)
        total = 0
        while True:
            count = query.delete(bulk = True)
            total += count
            if not count:
                return total

class Artist(db.Entity):
    _table_ = 'artist'

    id = PrimaryKey(UUID, default = uuid4)
    name = Required(str) # unique
    albums = Set(lambda: Album)
    tracks = Set(lambda: Track)

    stars = Set(lambda: StarredArtist)

    def as_subsonic_artist(self, user):
        info = dict(
            id = str(self.id),
            name = self.name,
            # coverArt
            albumCount = self.albums.count()
        )

        try:
            starred = StarredArtist[user.id, self.id]
            info['starred'] = starred.date.isoformat()
        except ObjectNotFound: pass

        return info

    @classmethod
    def prune(cls):
        return cls.select(lambda self: not exists(a for a in Album if a.artist == self) and \
            not exists(t for t in Track if t.artist == self)).delete(bulk = True)

class Album(db.Entity):
    _table_ = 'album'

    id = PrimaryKey(UUID, default = uuid4)
    name = Required(str)
    artist = Required(Artist, column = 'artist_id')
    tracks = Set(lambda: Track)

    stars = Set(lambda: StarredAlbum)

    def as_subsonic_album(self, user):
        info = dict(
            id = str(self.id),
            name = self.name,
            artist = self.artist.name,
            artistId = str(self.artist.id),
            songCount = self.tracks.count(),
            duration = sum(self.tracks.duration),
            created = min(self.tracks.created).isoformat()
        )

        track_with_cover = self.tracks.select(lambda t: t.folder.has_cover_art).first()
        if track_with_cover is not None:
            info['coverArt'] = str(track_with_cover.folder.id)

        try:
            starred = StarredAlbum[user.id, self.id]
            info['starred'] = starred.date.isoformat()
        except ObjectNotFound: pass

        return info

    def sort_key(self):
        year = min(map(lambda t: t.year if t.year else 9999, self.tracks))
        return '%i%s' % (year, self.name.lower())

    @classmethod
    def prune(cls):
        return cls.select(lambda self: not exists(t for t in Track if t.album == self)).delete(bulk = True)

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

    path = Required(str, 4096) # unique
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
        info = dict(
            id = str(self.id),
            parent = str(self.folder.id),
            isDir = False,
            title = self.title,
            album = self.album.name,
            artist = self.artist.name,
            track = self.number,
            size = os.path.getsize(self.path) if os.path.isfile(self.path) else -1,
            contentType = self.content_type,
            suffix = self.suffix(),
            duration = self.duration,
            bitRate = self.bitrate,
            path = self.path[len(self.root_folder.path) + 1:],
            isVideo = False,
            discNumber = self.disc,
            created = self.created.isoformat(),
            albumId = str(self.album.id),
            artistId = str(self.artist.id),
            type = 'music'
        )

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

        if prefs is not None and prefs.format is not None and prefs.format != self.suffix():
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
    name = Required(str, 64) # unique
    mail = Optional(str)
    password = Required(str, 40)
    salt = Required(str, 6)
    admin = Required(bool, default = False)
    lastfm_session = Optional(str, 32, nullable = True)
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
        return dict(
            username = self.name,
            email = self.mail,
            scrobblingEnabled = self.lastfm_session is not None and self.lastfm_status,
            adminRole = self.admin,
            settingsRole = True,
            downloadRole = True,
            uploadRole = False,
            playlistRole = True,
            coverArtRole = False,
            commentRole = False,
            podcastRole = False,
            streamRole = True,
            jukeboxRole = False,
            shareRole = False
        )

class ClientPrefs(db.Entity):
    _table_ = 'client_prefs'

    user = Required(User, column = 'user_id')
    client_name = Required(str, 32)
    PrimaryKey(user, client_name)
    format = Optional(str, 8, nullable = True)
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
    rating = Required(int, min = 1, max = 5)

    PrimaryKey(user, rated)

class RatingTrack(db.Entity):
    _table_ = 'rating_track'
    user = Required(User, column = 'user_id')
    rated = Required(Track, column = 'rated_id')
    rating = Required(int, min = 1, max = 5)

    PrimaryKey(user, rated)

class ChatMessage(db.Entity):
    _table_ = 'chat_message'

    id = PrimaryKey(UUID, default = uuid4)
    user = Required(User, column = 'user_id')
    time = Required(int, default = lambda: int(time.time()))
    message = Required(str, 512)

    def responsize(self):
        return dict(
            username = self.user.name,
            time = self.time * 1000,
            message = self.message
        )

class Playlist(db.Entity):
    _table_ = 'playlist'

    id = PrimaryKey(UUID, default = uuid4)
    user = Required(User, column = 'user_id')
    name = Required(str)
    comment = Optional(str)
    public = Required(bool, default = False)
    created = Required(datetime, precision = 0, default = now)
    tracks = Optional(LongStr)

    def as_subsonic_playlist(self, user):
        tracks = self.get_tracks()
        info = dict(
            id = str(self.id),
            name = self.name if self.user.id == user.id else '[%s] %s' % (self.user.name, self.name),
            owner = self.user.name,
            public = self.public,
            songCount = len(tracks),
            duration = sum(map(lambda t: t.duration, tracks)),
            created = self.created.isoformat()
        )
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
            except (ValueError, ObjectNotFound):
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
        elif isinstance(track, strtype):
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
    if not isinstance(database_uri, strtype):
        raise TypeError('Expecting a string')

    uri = urlparse(database_uri)
    args = dict(parse_qsl(uri.query))

    if uri.scheme == 'sqlite':
        path = uri.path
        if not path:
            path = ':memory:'
        elif path[0] == '/':
            path = path[1:]

        return dict(provider = 'sqlite', filename = path, **args)
    elif uri.scheme in ('postgres', 'postgresql'):
        return dict(provider = 'postgres', user = uri.username, password = uri.password, host = uri.hostname, dbname = uri.path[1:], **args)
    elif uri.scheme == 'mysql':
        args.setdefault('charset', 'utf8mb4')
        return dict(provider = 'mysql', user = uri.username, passwd = uri.password, host = uri.hostname, db = uri.path[1:], **args)
    return dict()

def init_database(database_uri, create_tables = False):
    db.bind(**parse_uri(database_uri))
    db.generate_mapping(create_tables = create_tables)

def release_database():
    db.disconnect()
    db.provider = None
    db.schema = None


# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import importlib
import mimetypes
import os.path
import pkg_resources
import time

from datetime import datetime
from hashlib import sha1
from pony.orm import Database, Required, Optional, Set, PrimaryKey, LongStr
from pony.orm import ObjectNotFound, DatabaseError
from pony.orm import buffer
from pony.orm import min, avg, sum, count, exists
from pony.orm import db_session
from urllib.parse import urlparse, parse_qsl
from uuid import UUID, uuid4

SCHEMA_VERSION = "20200607"


def now():
    return datetime.now().replace(microsecond=0)


metadb = Database()


class Meta(metadb.Entity):
    _table_ = "meta"
    key = PrimaryKey(str, 32)
    value = Required(str, 256)


db = Database()


@db.on_connect(provider="sqlite")
def sqlite_case_insensitive_like(db, connection):
    cursor = connection.cursor()
    cursor.execute("PRAGMA case_sensitive_like = OFF")


class PathMixin:
    @classmethod
    def get(cls, *args, **kwargs):
        if kwargs:
            path = kwargs.pop("path", None)
            if path:
                kwargs["_path_hash"] = sha1(path.encode("utf-8")).digest()
        return db.Entity.get.__func__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        path = kwargs["path"]
        kwargs["_path_hash"] = sha1(path.encode("utf-8")).digest()
        db.Entity.__init__(self, *args, **kwargs)

    def __setattr__(self, attr, value):
        db.Entity.__setattr__(self, attr, value)
        if attr == "path":
            db.Entity.__setattr__(
                self, "_path_hash", sha1(value.encode("utf-8")).digest()
            )


class Folder(PathMixin, db.Entity):
    _table_ = "folder"

    id = PrimaryKey(int, auto=True)
    root = Required(bool, default=False)
    name = Required(str, autostrip=False)
    path = Required(str, 4096, autostrip=False)  # unique
    _path_hash = Required(buffer, column="path_hash")
    created = Required(datetime, precision=0, default=now)
    cover_art = Optional(str, nullable=True, autostrip=False)
    last_scan = Required(int, default=0)

    parent = Optional(lambda: Folder, reverse="children", column="parent_id")
    children = Set(lambda: Folder, reverse="parent")

    __alltracks = Set(
        lambda: Track, lazy=True, reverse="root_folder"
    )  # Never used, hide it. Could be huge, lazy load
    tracks = Set(lambda: Track, reverse="folder")

    stars = Set(lambda: StarredFolder)
    ratings = Set(lambda: RatingFolder)

    def as_subsonic_child(self, user):
        info = {
            "id": str(self.id),
            "isDir": True,
            "title": self.name,
            "album": self.name,
            "created": self.created.isoformat(),
        }
        if not self.root:
            info["parent"] = str(self.parent.id)
            info["artist"] = self.parent.name
        if self.cover_art:
            info["coverArt"] = str(self.id)
        else:
            for track in self.tracks:
                if track.has_art:
                    info["coverArt"] = str(track.id)
                    break

        try:
            starred = StarredFolder[user.id, self.id]
            info["starred"] = starred.date.isoformat()
        except ObjectNotFound:
            pass

        try:
            rating = RatingFolder[user.id, self.id]
            info["userRating"] = rating.rating
        except ObjectNotFound:
            pass

        avgRating = avg(self.ratings.rating)
        if avgRating:
            info["averageRating"] = avgRating

        return info

    def as_subsonic_artist(self, user):  # "Artist" type in XSD
        info = {"id": str(self.id), "name": self.name}

        try:
            starred = StarredFolder[user.id, self.id]
            info["starred"] = starred.date.isoformat()
        except ObjectNotFound:
            pass

        return info

    def as_subsonic_directory(self, user, client):  # "Directory" type in XSD
        info = {
            "id": str(self.id),
            "name": self.name,
            "child": [
                f.as_subsonic_child(user)
                for f in self.children.order_by(lambda c: c.name.lower())
            ]
            + [
                t.as_subsonic_child(user, client)
                for t in sorted(self.tracks, key=lambda t: t.sort_key())
            ],
        }
        if not self.root:
            info["parent"] = str(self.parent.id)

        return info

    @classmethod
    def prune(cls):
        query = cls.select(
            lambda self: not exists(t for t in Track if t.folder == self)
            and not exists(f for f in Folder if f.parent == self)
            and not self.root
        )
        total = 0
        while True:
            count = query.delete()
            total += count
            if not count:
                return total


class Artist(db.Entity):
    _table_ = "artist"

    id = PrimaryKey(UUID, default=uuid4)
    name = Required(str)  # unique
    albums = Set(lambda: Album)
    tracks = Set(lambda: Track)

    stars = Set(lambda: StarredArtist)

    def as_subsonic_artist(self, user):
        info = {
            "id": str(self.id),
            "name": self.name,
            # coverArt
            "albumCount": self.albums.count(),
        }

        try:
            starred = StarredArtist[user.id, self.id]
            info["starred"] = starred.date.isoformat()
        except ObjectNotFound:
            pass

        return info

    @classmethod
    def prune(cls):
        return cls.select(
            lambda self: not exists(a for a in Album if a.artist == self)
            and not exists(t for t in Track if t.artist == self)
        ).delete()


class Album(db.Entity):
    _table_ = "album"

    id = PrimaryKey(UUID, default=uuid4)
    name = Required(str)
    artist = Required(Artist, column="artist_id")
    tracks = Set(lambda: Track)

    stars = Set(lambda: StarredAlbum)

    def as_subsonic_album(self, user):  # "AlbumID3" type in XSD
        info = {
            "id": str(self.id),
            "name": self.name,
            "artist": self.artist.name,
            "artistId": str(self.artist.id),
            "songCount": self.tracks.count(),
            "duration": sum(self.tracks.duration),
            "created": min(self.tracks.created).isoformat(),
        }

        track_with_cover = self.tracks.select(
            lambda t: t.folder.cover_art is not None
        ).first()
        if track_with_cover is not None:
            info["coverArt"] = str(track_with_cover.folder.id)
        else:
            track_with_cover = self.tracks.select(lambda t: t.has_art).first()
            if track_with_cover is not None:
                info["coverArt"] = str(track_with_cover.id)

        if count(self.tracks.year) > 0:
            info["year"] = min(self.tracks.year)

        genre = ", ".join(self.tracks.genre.distinct())
        if genre:
            info["genre"] = genre

        try:
            starred = StarredAlbum[user.id, self.id]
            info["starred"] = starred.date.isoformat()
        except ObjectNotFound:
            pass

        return info

    def sort_key(self):
        year = min(t.year if t.year else 9999 for t in self.tracks)
        return f"{year}{self.name.lower()}"

    @classmethod
    def prune(cls):
        return cls.select(
            lambda self: not exists(t for t in Track if t.album == self)
        ).delete()


class Track(PathMixin, db.Entity):
    _table_ = "track"

    id = PrimaryKey(UUID, default=uuid4)
    disc = Required(int)
    number = Required(int)
    title = Required(str)
    year = Optional(int)
    genre = Optional(str, nullable=True)
    duration = Required(int)
    has_art = Required(bool, default=False)

    album = Required(Album, column="album_id")
    artist = Required(Artist, column="artist_id")

    bitrate = Required(int)

    path = Required(str, 4096, autostrip=False)  # unique
    _path_hash = Required(buffer, column="path_hash")
    created = Required(datetime, precision=0, default=now)
    last_modification = Required(int)

    play_count = Required(int, default=0)
    last_play = Optional(datetime, precision=0)

    root_folder = Required(Folder, column="root_folder_id")
    folder = Required(Folder, column="folder_id")

    __lastly_played_by = Set(lambda: User)  # Never used, hide it

    stars = Set(lambda: StarredTrack)
    ratings = Set(lambda: RatingTrack)

    def as_subsonic_child(self, user, prefs):
        info = {
            "id": str(self.id),
            "parent": str(self.folder.id),
            "isDir": False,
            "title": self.title,
            "album": self.album.name,
            "artist": self.artist.name,
            "track": self.number,
            "size": os.path.getsize(self.path) if os.path.isfile(self.path) else -1,
            "contentType": self.mimetype,
            "suffix": self.suffix(),
            "duration": self.duration,
            "bitRate": self.bitrate,
            "path": self.path[len(self.root_folder.path) + 1 :],
            "isVideo": False,
            "discNumber": self.disc,
            "created": self.created.isoformat(),
            "albumId": str(self.album.id),
            "artistId": str(self.artist.id),
            "type": "music",
        }

        if self.year:
            info["year"] = self.year
        if self.genre:
            info["genre"] = self.genre
        if self.has_art:
            info["coverArt"] = str(self.id)
        elif self.folder.cover_art:
            info["coverArt"] = str(self.folder.id)

        try:
            starred = StarredTrack[user.id, self.id]
            info["starred"] = starred.date.isoformat()
        except ObjectNotFound:
            pass

        try:
            rating = RatingTrack[user.id, self.id]
            info["userRating"] = rating.rating
        except ObjectNotFound:
            pass

        avgRating = avg(self.ratings.rating)
        if avgRating:
            info["averageRating"] = avgRating

        if (
            prefs is not None
            and prefs.format is not None
            and prefs.format != self.suffix()
        ):
            info["transcodedSuffix"] = prefs.format
            info["transcodedContentType"] = (
                mimetypes.guess_type("dummyname." + prefs.format, False)[0]
                or "application/octet-stream"
            )

        return info

    @property
    def mimetype(self):
        return mimetypes.guess_type(self.path, False)[0] or "application/octet-stream"

    def duration_str(self):
        ret = "{:02}:{:02}".format((self.duration % 3600) / 60, self.duration % 60)
        if self.duration >= 3600:
            ret = "{:02}:{}".format(self.duration / 3600, ret)
        return ret

    def suffix(self):
        return os.path.splitext(self.path)[1][1:].lower()

    def sort_key(self):
        return f"{self.album.artist.name}{self.album.name}{self.disc:02}{self.number:02}{self.title}".lower()


class User(db.Entity):
    _table_ = "user"

    id = PrimaryKey(UUID, default=uuid4)
    name = Required(str, 64)  # unique
    mail = Optional(str)
    password = Required(str, 40)
    salt = Required(str, 6)

    admin = Required(bool, default=False)
    jukebox = Required(bool, default=False)

    lastfm_session = Optional(str, 32, nullable=True)
    lastfm_status = Required(
        bool, default=True
    )  # True: ok/unlinked, False: invalid session

    last_play = Optional(Track, column="last_play_id")
    last_play_date = Optional(datetime, precision=0)

    clients = Set(lambda: ClientPrefs)
    playlists = Set(lambda: Playlist)
    __messages = Set(lambda: ChatMessage, lazy=True)  # Never used, hide it

    starred_folders = Set(lambda: StarredFolder, lazy=True)
    starred_artists = Set(lambda: StarredArtist, lazy=True)
    starred_albums = Set(lambda: StarredAlbum, lazy=True)
    starred_tracks = Set(lambda: StarredTrack, lazy=True)
    folder_ratings = Set(lambda: RatingFolder, lazy=True)
    track_ratings = Set(lambda: RatingTrack, lazy=True)

    def as_subsonic_user(self):
        return {
            "username": self.name,
            "email": self.mail,
            "scrobblingEnabled": self.lastfm_session is not None and self.lastfm_status,
            "adminRole": self.admin,
            "settingsRole": True,
            "downloadRole": True,
            "uploadRole": False,
            "playlistRole": True,
            "coverArtRole": False,
            "commentRole": False,
            "podcastRole": False,
            "streamRole": True,
            "jukeboxRole": self.admin or self.jukebox,
            "shareRole": False,
        }


class ClientPrefs(db.Entity):
    _table_ = "client_prefs"

    user = Required(User, column="user_id")
    client_name = Required(str, 32)
    PrimaryKey(user, client_name)
    format = Optional(str, 8, nullable=True)
    bitrate = Optional(int)


class StarredFolder(db.Entity):
    _table_ = "starred_folder"

    user = Required(User, column="user_id")
    starred = Required(Folder, column="starred_id")
    date = Required(datetime, precision=0, default=now)

    PrimaryKey(user, starred)


class StarredArtist(db.Entity):
    _table_ = "starred_artist"

    user = Required(User, column="user_id")
    starred = Required(Artist, column="starred_id")
    date = Required(datetime, precision=0, default=now)

    PrimaryKey(user, starred)


class StarredAlbum(db.Entity):
    _table_ = "starred_album"

    user = Required(User, column="user_id")
    starred = Required(Album, column="starred_id")
    date = Required(datetime, precision=0, default=now)

    PrimaryKey(user, starred)


class StarredTrack(db.Entity):
    _table_ = "starred_track"

    user = Required(User, column="user_id")
    starred = Required(Track, column="starred_id")
    date = Required(datetime, precision=0, default=now)

    PrimaryKey(user, starred)


class RatingFolder(db.Entity):
    _table_ = "rating_folder"
    user = Required(User, column="user_id")
    rated = Required(Folder, column="rated_id")
    rating = Required(int, min=1, max=5)

    PrimaryKey(user, rated)


class RatingTrack(db.Entity):
    _table_ = "rating_track"
    user = Required(User, column="user_id")
    rated = Required(Track, column="rated_id")
    rating = Required(int, min=1, max=5)

    PrimaryKey(user, rated)


class ChatMessage(db.Entity):
    _table_ = "chat_message"

    id = PrimaryKey(UUID, default=uuid4)
    user = Required(User, column="user_id")
    time = Required(int, default=lambda: int(time.time()))
    message = Required(str, 512)

    def responsize(self):
        return {
            "username": self.user.name,
            "time": self.time * 1000,
            "message": self.message,
        }


class Playlist(db.Entity):
    _table_ = "playlist"

    id = PrimaryKey(UUID, default=uuid4)
    user = Required(User, column="user_id")
    name = Required(str)
    comment = Optional(str)
    public = Required(bool, default=False)
    created = Required(datetime, precision=0, default=now)
    tracks = Optional(LongStr)

    def as_subsonic_playlist(self, user):
        tracks = self.get_tracks()
        info = {
            "id": str(self.id),
            "name": self.name
            if self.user.id == user.id
            else "[{}] {}".format(self.user.name, self.name),
            "owner": self.user.name,
            "public": self.public,
            "songCount": len(tracks),
            "duration": sum(t.duration for t in tracks),
            "created": self.created.isoformat(),
        }
        if self.comment:
            info["comment"] = self.comment
        return info

    def get_tracks(self):
        if not self.tracks:
            return []

        tracks = []
        should_fix = False

        for t in self.tracks.split(","):
            try:
                tid = UUID(t)
                track = Track[tid]
                tracks.append(track)
            except (ValueError, ObjectNotFound):
                should_fix = True

        if should_fix:
            self.tracks = ",".join(str(t.id) for t in tracks)
            db.commit()

        return tracks

    def clear(self):
        self.tracks = ""

    def add(self, track):
        if isinstance(track, UUID):
            tid = track
        elif isinstance(track, Track):
            tid = track.id
        elif isinstance(track, str):
            tid = UUID(track)

        if self.tracks and len(self.tracks) > 0:
            self.tracks = "{},{}".format(self.tracks, tid)
        else:
            self.tracks = str(tid)

    def remove_at_indexes(self, indexes):
        tracks = self.tracks.split(",")
        for i in indexes:
            if i < 0 or i >= len(tracks):
                continue
            tracks[i] = None

        self.tracks = ",".join(t for t in tracks if t)


class RadioStation(db.Entity):
    _table_ = "radio_station"

    id = PrimaryKey(UUID, default=uuid4)
    stream_url = Required(str)
    name = Required(str)
    homepage_url = Optional(str, nullable=True)
    created = Required(datetime, precision=0, default=now)

    def as_subsonic_station(self):
        info = {
            "id": str(self.id),
            "streamUrl": self.stream_url,
            "name": self.name,
            "homePageUrl": self.homepage_url,
        }
        return info


def parse_uri(database_uri):
    if not isinstance(database_uri, str):
        raise TypeError("Expecting a string")

    uri = urlparse(database_uri)
    args = dict(parse_qsl(uri.query))
    if uri.port is not None:
        args["port"] = uri.port

    if uri.scheme == "sqlite":
        path = uri.path
        if not path:
            path = ":memory:"
        elif path[0] == "/":
            path = path[1:]

        return {"provider": "sqlite", "filename": path, "create_db": True, **args}
    elif uri.scheme in ("postgres", "postgresql"):
        return {
            "provider": "postgres",
            "user": uri.username,
            "password": uri.password,
            "host": uri.hostname,
            "dbname": uri.path[1:],
            **args,
        }
    elif uri.scheme == "mysql":
        args.setdefault("charset", "utf8mb4")
        args.setdefault("binary_prefix", True)
        return {
            "provider": "mysql",
            "user": uri.username,
            "passwd": uri.password,
            "host": uri.hostname,
            "db": uri.path[1:],
            **args,
        }
    return {}


def execute_sql_resource_script(respath):
    sql = pkg_resources.resource_string(__package__, respath).decode("utf-8")
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("--"):
            metadb.execute(statement)


def init_database(database_uri):
    settings = parse_uri(database_uri)

    metadb.bind(**settings)
    metadb.generate_mapping(check_tables=False)

    # Check if we should create the tables
    try:
        metadb.check_tables()
    except DatabaseError:
        with db_session:
            execute_sql_resource_script("schema/" + settings["provider"] + ".sql")
            Meta(key="schema_version", value=SCHEMA_VERSION)

    # Check for schema changes
    with db_session:
        version = Meta["schema_version"]
        if version.value < SCHEMA_VERSION:
            migrations = sorted(
                pkg_resources.resource_listdir(
                    __package__, "schema/migration/" + settings["provider"]
                )
            )
            for migration in migrations:
                date, ext = os.path.splitext(migration)
                if date <= version.value:
                    continue
                if ext == ".sql":
                    execute_sql_resource_script(
                        "schema/migration/{}/{}".format(settings["provider"], migration)
                    )
                elif ext == ".py":
                    m = importlib.import_module(
                        ".schema.migration.{}.{}".format(settings["provider"], date),
                        __package__,
                    )
                    m.apply(settings.copy())
            version.value = SCHEMA_VERSION

    # Hack for in-memory SQLite databases (used in tests), otherwise 'db' and 'metadb' would be two distinct databases
    # and 'db' wouldn't have any table
    if settings["provider"] == "sqlite" and settings["filename"] == ":memory:":
        db.provider = metadb.provider
    else:
        metadb.disconnect()
        db.bind(**settings)
        # Force requests to Meta to use the same connection as other tables
        metadb.provider = db.provider

    db.generate_mapping(check_tables=False)


def release_database():
    metadb.disconnect()
    db.disconnect()
    db.provider = metadb.provider = None
    db.schema = metadb.schema = None

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2024 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import importlib
import mimetypes
import os.path
import sys
import time

from datetime import datetime
from hashlib import sha1
from peewee import (
    AutoField,
    BlobField,
    BooleanField,
    CharField,
    DateTimeField,
    FixedCharField,
    ForeignKeyField,
    IntegerField,
    TextField,
    UUIDField,
)
from peewee import CompositeKey, DatabaseProxy, Model, MySQLDatabase
from peewee import fn
from playhouse.db_url import parseresult_to_dict, schemes
from urllib.parse import urlparse
from uuid import UUID, uuid4

SCHEMA_VERSION = "20240318"


def now():
    return datetime.now().replace(microsecond=0)


def random():
    if isinstance(db.obj, MySQLDatabase):
        return fn.rand()
    return fn.random()


def PrimaryKeyField(**kwargs):
    return UUIDField(primary_key=True, default=uuid4, **kwargs)


db = DatabaseProxy()


class _Model(Model):
    class Meta:
        database = db
        legacy_table_names = False


class Meta(_Model):
    key = CharField(32, primary_key=True)
    value = CharField(256)


class PathMixin:
    @classmethod
    def get(cls, *args, **kwargs):
        if kwargs:
            path = kwargs.pop("path", None)
            if path:
                kwargs["_path_hash"] = sha1(path.encode("utf-8")).digest()
        return _Model.get.__func__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        if "path" in kwargs:
            path = kwargs["path"]
            kwargs["_path_hash"] = sha1(path.encode("utf-8")).digest()
        _Model.__init__(self, *args, **kwargs)

    def __setattr__(self, attr, value):
        _Model.__setattr__(self, attr, value)
        if attr == "path":
            _Model.__setattr__(self, "_path_hash", sha1(value.encode("utf-8")).digest())


class Folder(PathMixin, _Model):
    id = AutoField()
    root = BooleanField()
    name = CharField()
    path = CharField(4096)  # unique
    _path_hash = BlobField(column_name="path_hash", unique=True)
    created = DateTimeField(default=now)
    cover_art = CharField(null=True)
    last_scan = IntegerField(default=0)

    parent = ForeignKeyField("self", null=True, backref="children")

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
        except StarredFolder.DoesNotExist:
            pass

        try:
            rating = RatingFolder[user.id, self.id]
            info["userRating"] = rating.rating
        except RatingFolder.DoesNotExist:
            pass

        avgRating = (
            RatingFolder.select(fn.avg(RatingFolder.rating, coerce=False))
            .where(RatingFolder.rated == self)
            .scalar()
        )
        if avgRating:
            info["averageRating"] = avgRating

        return info

    def as_subsonic_artist(self, user):  # "Artist" type in XSD
        info = {"id": str(self.id), "name": self.name}

        try:
            starred = StarredFolder[user.id, self.id]
            info["starred"] = starred.date.isoformat()
        except StarredFolder.DoesNotExist:
            pass

        return info

    def as_subsonic_directory(self, user, client):  # "Directory" type in XSD
        info = {
            "id": str(self.id),
            "name": self.name,
            "child": [
                f.as_subsonic_child(user)
                for f in self.children.order_by(fn.lower(Folder.name))
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
        alias = cls.alias()
        query = cls.select(cls.id).where(
            ~cls.root,
            Track.select(fn.count("*")).where(Track.folder == cls.id) == 0,
            alias.select(fn.count("*")).where(alias.parent == cls.id) == 0,
        )
        total = 0
        while True:
            clone = query.clone()  # peewee caches the results, clone to force a refetch
            for f in clone:
                f.delete_instance(recursive=True)
                total += 1
            if not len(clone):
                return total

    def delete_hierarchy(self):
        if self.root:
            cond = Track.root_folder == self
        else:
            cond = Track.path.startswith(self.path)

        return self.__delete_hierarchy(cond)

    def __delete_hierarchy(self, cond):
        users = User.select(User.id).join(Track).where(cond)
        User.update(last_play=None).where(User.id.in_(users)).execute()

        tracks = Track.select(Track.id).where(cond)
        RatingTrack.delete().where(RatingTrack.rated.in_(tracks)).execute()
        StarredTrack.delete().where(StarredTrack.starred.in_(tracks)).execute()

        path_cond = Folder.path.startswith(self.path)
        folders = Folder.select(Folder.id).where(path_cond)
        RatingFolder.delete().where(RatingFolder.rated.in_(folders)).execute()
        StarredFolder.delete().where(StarredFolder.starred.in_(folders)).execute()

        deleted_tracks = Track.delete().where(cond).execute()

        query = Folder.delete().where(path_cond)
        if isinstance(db.obj, MySQLDatabase):
            # MySQL can't propery resolve deletion order when it has several to handle
            query = query.order_by(Folder.path.desc())
        query.execute()

        return deleted_tracks


class Artist(_Model):
    id = PrimaryKeyField()
    name = CharField()

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
        except StarredArtist.DoesNotExist:
            pass

        return info

    @classmethod
    def prune(cls):
        album_artists = Album.select(Album.artist)
        track_artists = Track.select(Track.artist)

        StarredArtist.delete().where(
            StarredArtist.starred.not_in(album_artists),
            StarredArtist.starred.not_in(track_artists),
        ).execute()

        return (
            cls.delete()
            .where(
                cls.id.not_in(album_artists),
                cls.id.not_in(track_artists),
            )
            .execute()
        )


class Album(_Model):
    id = PrimaryKeyField()
    name = CharField()
    artist = ForeignKeyField(Artist, backref="albums")

    def as_subsonic_album(self, user):  # "AlbumID3" type in XSD
        duration, created, year = self.tracks.select(
            fn.sum(Track.duration), fn.min(Track.created), fn.min(Track.year)
        ).scalar(as_tuple=True)

        info = {
            "id": str(self.id),
            "name": self.name,
            "artist": self.artist.name,
            "artistId": str(self.artist.id),
            "songCount": self.tracks.count(),
            "duration": duration,
            "created": created.isoformat(),
        }

        track_with_cover = (
            self.tracks.join(Folder).where(Folder.cover_art.is_null(False)).first()
        )
        if track_with_cover is not None:
            info["coverArt"] = str(track_with_cover.folder.id)
        else:
            track_with_cover = self.tracks.where(Track.has_art).first()
            if track_with_cover is not None:
                info["coverArt"] = str(track_with_cover.id)

        if year:
            info["year"] = year

        genre = ", ".join(
            g
            for (g,) in self.tracks.select(Track.genre)
            .where(Track.genre.is_null(False))
            .distinct()
            .tuples()
        )
        if genre:
            info["genre"] = genre

        try:
            starred = StarredAlbum[user.id, self.id]
            info["starred"] = starred.date.isoformat()
        except StarredAlbum.DoesNotExist:
            pass

        return info

    def sort_key(self):
        year = self.tracks.select(fn.min(Track.year)).scalar() or 9999
        return f"{year}{self.name.lower()}"

    @classmethod
    def prune(cls):
        albums = Track.select(Track.album)
        StarredAlbum.delete().where(StarredAlbum.starred.not_in(albums)).execute()
        return cls.delete().where(cls.id.not_in(albums)).execute()


class Track(PathMixin, _Model):
    id = PrimaryKeyField()
    disc = IntegerField()
    number = IntegerField()
    title = CharField()
    year = IntegerField(null=True)
    genre = CharField(null=True)
    duration = IntegerField()
    has_art = BooleanField(default=False)

    album = ForeignKeyField(Album, backref="tracks")
    artist = ForeignKeyField(Artist, backref="tracks")

    bitrate = IntegerField()

    path = CharField(4096)  # unique
    _path_hash = BlobField(column_name="path_hash", unique=True)
    created = DateTimeField(default=now)
    last_modification = IntegerField()

    play_count = IntegerField(default=0)
    last_play = DateTimeField(null=True)

    root_folder = ForeignKeyField(Folder, backref="+")
    folder = ForeignKeyField(Folder, backref="tracks")

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
        except StarredTrack.DoesNotExist:
            pass

        try:
            rating = RatingTrack[user.id, self.id]
            info["userRating"] = rating.rating
        except RatingTrack.DoesNotExist:
            pass

        avgRating = (
            RatingTrack.select(fn.avg(RatingTrack.rating, coerce=False))
            .where(RatingTrack.rated == self)
            .scalar()
        )
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
        ret = f"{(self.duration % 3600) / 60:02}:{self.duration % 60:02}"
        if self.duration >= 3600:
            ret = f"{self.duration / 3600:02}:{ret}"
        return ret

    def suffix(self):
        return os.path.splitext(self.path)[1][1:].lower()

    def sort_key(self):
        return f"{self.album.artist.name}{self.album.name}{self.disc:02}{self.number:02}{self.title}".lower()


class User(_Model):
    id = PrimaryKeyField()
    name = CharField(64, unique=True)
    mail = CharField(null=True)
    password = FixedCharField(40)
    salt = FixedCharField(6)

    admin = BooleanField(default=False)
    jukebox = BooleanField(default=False)

    lastfm_session = FixedCharField(32, null=True)
    lastfm_status = BooleanField(
        default=True
    )  # True: ok/unlinked, False: invalid session

    listenbrainz_session = FixedCharField(36, null=True)
    listenbrainz_status = BooleanField(
        default=True
    )  # True: ok/unlinked, False: invalid token

    last_play = ForeignKeyField(Track, null=True, backref="+")
    last_play_date = DateTimeField(null=True)

    def as_subsonic_user(self):
        return {
            "username": self.name,
            "email": self.mail or "",
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


class ClientPrefs(_Model):
    user = ForeignKeyField(User, backref="clients")
    client_name = CharField(32)
    format = CharField(8, null=True)
    bitrate = IntegerField(null=True)

    class Meta:
        primary_key = CompositeKey("user", "client_name")


def _make_starred_model(target_model):
    class Starred(_Model):
        user = ForeignKeyField(User, backref="+")
        starred = ForeignKeyField(target_model, backref="+")
        date = DateTimeField(default=now)

        class Meta:
            primary_key = CompositeKey("user", "starred")
            table_name = "starred_" + target_model._meta.table_name

    return Starred


StarredFolder = _make_starred_model(Folder)
StarredArtist = _make_starred_model(Artist)
StarredAlbum = _make_starred_model(Album)
StarredTrack = _make_starred_model(Track)


def _make_rating_model(target_model):
    class Rating(_Model):
        user = ForeignKeyField(User, backref="+")
        rated = ForeignKeyField(target_model, backref="+")
        rating = IntegerField()  # min=1, max=5

        class Meta:
            primary_key = CompositeKey("user", "rated")
            table_name = "rating_" + target_model._meta.table_name

    return Rating


RatingFolder = _make_rating_model(Folder)
RatingTrack = _make_rating_model(Track)


class ChatMessage(_Model):
    id = PrimaryKeyField()
    user = ForeignKeyField(User, backref="+")
    time = IntegerField(default=lambda: int(time.time()))
    message = CharField(512)

    def responsize(self):
        return {
            "username": self.user.name,
            "time": self.time * 1000,
            "message": self.message,
        }


class Playlist(_Model):
    id = PrimaryKeyField()
    user = ForeignKeyField(User, backref="playlists")
    name = CharField()
    comment = CharField(null=True)
    public = BooleanField(default=False)
    created = DateTimeField(default=now)
    tracks = TextField(null=True)

    def as_subsonic_playlist(self, user):
        tracks = self.get_tracks()
        info = {
            "id": str(self.id),
            "name": (
                self.name
                if self.user.id == user.id
                else f"[{self.user.name}] {self.name}"
            ),
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
            except (ValueError, Track.DoesNotExist):
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
            self.tracks = f"{self.tracks},{tid}"
        else:
            self.tracks = str(tid)

    def remove_at_indexes(self, indexes):
        tracks = self.tracks.split(",")
        for i in indexes:
            if i < 0 or i >= len(tracks):
                continue
            tracks[i] = None

        self.tracks = ",".join(t for t in tracks if t)


class RadioStation(_Model):
    id = PrimaryKeyField()
    stream_url = CharField()
    name = CharField()
    homepage_url = CharField(null=True)
    created = DateTimeField(default=now)

    def as_subsonic_station(self):
        info = {
            "id": str(self.id),
            "streamUrl": self.stream_url,
            "name": self.name,
            "homePageUrl": self.homepage_url,
        }
        return info


if sys.version_info < (3, 9):
    import pkg_resources

    def get_resource_text(respath):
        return pkg_resources.resource_string(__package__, respath).decode("utf-8")

    def list_migrations(provider):
        return pkg_resources.resource_listdir(
            __package__, f"schema/migration/{provider}"
        )

else:
    import importlib.resources

    def get_resource_text(respath):
        return (
            importlib.resources.files(__package__).joinpath(respath).read_text("utf-8")
        )

    def list_migrations(provider):
        return (
            e.name
            for e in importlib.resources.files(__package__)
            .joinpath(f"schema/migration/{provider}")
            .iterdir()
        )


def execute_sql_resource_script(respath):
    sql = get_resource_text(respath)
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement and not statement.startswith("--"):
            db.execute_sql(statement)


def init_database(database_uri):
    uri = urlparse(database_uri)
    args = parseresult_to_dict(uri)
    if uri.scheme.startswith("mysql"):
        args.setdefault("charset", "utf8mb4")
        args.setdefault("binary_prefix", True)

    if uri.scheme.startswith("mysql"):
        provider = "mysql"
    elif uri.scheme.startswith("postgres"):
        provider = "postgres"
    elif uri.scheme.startswith("sqlite"):
        provider = "sqlite"
        args["pragmas"] = {"foreign_keys": 1}
    else:
        raise RuntimeError(f"Unsupported database: {uri.scheme}")

    db_class = schemes.get(uri.scheme)
    db.initialize(db_class(**args))
    db.connect()

    # Check if we should create the tables
    if not db.table_exists("meta"):
        with db.atomic():
            execute_sql_resource_script(f"schema/{provider}.sql")
            Meta.create(key="schema_version", value=SCHEMA_VERSION)

    # Check for schema changes
    version = Meta["schema_version"]
    if version.value < SCHEMA_VERSION:
        args.pop("pragmas", ())
        migrations = sorted(list_migrations(provider))
        for migration in migrations:
            if migration[0] in ("_", "."):
                continue

            date, ext = os.path.splitext(migration)
            if date <= version.value:
                continue

            if ext == ".sql":
                with db.atomic():
                    execute_sql_resource_script(
                        f"schema/migration/{provider}/{migration}"
                    )
            elif ext == ".py":
                m = importlib.import_module(
                    f".schema.migration.{provider}.{date}", __package__
                )
                m.apply(args.copy())

        version.value = SCHEMA_VERSION
        version.save()


def release_database():
    db.close()
    db.initialize(None)


def open_connection(reuse=False):
    return db.connect(reuse)


def close_connection():
    db.close()

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import mimetypes
import os.path
import time
from datetime import datetime
from functools import partial
from hashlib import sha1
from uuid import UUID, uuid4

from peewee import (
    AutoField,
    BigIntegerField,
    BlobField,
    BooleanField,
    CharField,
    CompositeKey,
    DateTimeField as _DTField,
    FixedCharField,
    ForeignKeyField,
    IntegerField,
    MySQLDatabase,
    UUIDField,
    fn,
)

from ..pathutils import subpath_expr
from .proxy import Model, db

PrimaryKeyField = partial(UUIDField, primary_key=True, default=uuid4)


class DateTimeField(_DTField):
    """Datetime field, stored without timezone (mostly because peewee+SQLite don't
    handle them properly)
    """

    def db_value(self, value):
        if isinstance(value, datetime):
            value = value.replace(tzinfo=None)
        return super().db_value(value)


class Meta(Model):
    key = CharField(32, primary_key=True)
    value = CharField(256)


class PathMixin:
    @staticmethod
    def _hash_path(path):
        return sha1(path.encode("utf-8")).digest()

    @classmethod
    def get(cls, *args, **kwargs):
        if kwargs:
            path = kwargs.pop("path", None)
            if path:
                kwargs["_path_hash"] = cls._hash_path(path)
        return super().get(*args, **kwargs)

    def save(self, *args, **kwargs):
        if "path" in self._dirty:
            self._path_hash = self._hash_path(self.path)
        return super().save(*args, **kwargs)


class Folder(PathMixin, Model):
    id = AutoField()
    root = BooleanField()
    name = CharField()
    path = CharField(4096)  # unique
    _path_hash = BlobField(column_name="path_hash", unique=True)
    created = DateTimeField(default=datetime.now)
    cover_art = CharField(null=True)
    last_scan = IntegerField(default=0)

    parent = ForeignKeyField("self", null=True, backref="children")

    def as_subsonic_child(self, ctx):
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
            cover = ctx.folder_cover(self.id)
            if cover is not None:
                info["coverArt"] = cover

        starred = ctx.starred_date(StarredFolder, self.id)
        if starred is not None:
            info["starred"] = starred

        rating = ctx.user_rating(RatingFolder, self.id)
        if rating is not None:
            info["userRating"] = rating

        avgRating = ctx.avg_rating(RatingFolder, self.id)
        if avgRating:
            info["averageRating"] = avgRating

        return info

    def as_subsonic_artist(self, ctx):  # "Artist" type in XSD
        info = {"id": str(self.id), "name": self.name}

        starred = ctx.starred_date(StarredFolder, self.id)
        if starred is not None:
            info["starred"] = starred

        return info

    def as_subsonic_directory(self, ctx):  # "Directory" type in XSD
        children = list(self.children.order_by(fn.lower(Folder.name)))
        tracks = list(self.tracks)
        ctx.add_folders(children)
        ctx.add_tracks(tracks)  # preload FKs before sort_key (reads album.artist)
        tracks.sort(key=lambda t: t.sort_key())

        info = {
            "id": str(self.id),
            "name": self.name,
            "child": [f.as_subsonic_child(ctx) for f in children]
            + [t.as_subsonic_child(ctx) for t in tracks],
        }
        if not self.root:
            info["parent"] = str(self.parent.id)

        return info

    @classmethod
    @db.atomic()
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
            cond = subpath_expr(Track.path, self.path)

        return self.__delete_hierarchy(cond)

    @db.atomic()
    def __delete_hierarchy(self, cond):
        users = User.select(User.id).join(Track).where(cond)
        User.update(last_play=None).where(User.id.in_(users)).execute()

        tracks = Track.select(Track.id).where(cond)
        PlaylistTrack.delete().where(PlaylistTrack.track.in_(tracks)).execute()
        RatingTrack.delete().where(RatingTrack.rated.in_(tracks)).execute()
        StarredTrack.delete().where(StarredTrack.starred.in_(tracks)).execute()

        path_cond = subpath_expr(Folder.path, self.path)
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


class Artist(Model):
    id = PrimaryKeyField()
    name = CharField()

    def as_subsonic_artist(self, ctx):
        info = {
            "id": str(self.id),
            "name": self.name,
            # coverArt
            "albumCount": ctx.artist_album_count(self.id),
        }

        starred = ctx.starred_date(StarredArtist, self.id)
        if starred is not None:
            info["starred"] = starred

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


class Album(Model):
    id = PrimaryKeyField()
    name = CharField()
    artist = ForeignKeyField(Artist, backref="albums")

    def as_subsonic_album(self, ctx):  # "AlbumID3" type in XSD
        duration, created, year, song_count = ctx.album_aggregate(self.id)

        info = {
            "id": str(self.id),
            "name": self.name,
            "artist": self.artist.name,
            "artistId": str(self.artist.id),
            "songCount": song_count,
            "duration": duration,
            "created": created.isoformat(),
        }

        cover = ctx.album_cover(self.id)
        if cover is not None:
            info["coverArt"] = cover

        if year:
            info["year"] = year

        genre = ctx.album_genre(self.id)
        if genre:
            info["genre"] = genre

        starred = ctx.starred_date(StarredAlbum, self.id)
        if starred is not None:
            info["starred"] = starred

        return info

    @classmethod
    def prune(cls):
        albums = Track.select(Track.album)
        StarredAlbum.delete().where(StarredAlbum.starred.not_in(albums)).execute()
        return cls.delete().where(cls.id.not_in(albums)).execute()


class Track(PathMixin, Model):
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
    size = BigIntegerField(default=0)

    path = CharField(4096)  # unique
    _path_hash = BlobField(column_name="path_hash", unique=True)
    created = DateTimeField(default=datetime.now)
    last_modification = IntegerField()

    play_count = IntegerField(default=0)
    last_play = DateTimeField(null=True)

    root_folder = ForeignKeyField(Folder, backref="+")
    folder = ForeignKeyField(Folder, backref="tracks")

    def as_subsonic_child(self, ctx):
        prefs = ctx.prefs
        info = {
            "id": str(self.id),
            "parent": str(self.folder.id),
            "isDir": False,
            "title": self.title,
            "album": self.album.name,
            "artist": self.artist.name,
            "track": self.number,
            "size": self.size,
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

        starred = ctx.starred_date(StarredTrack, self.id)
        if starred is not None:
            info["starred"] = starred

        rating = ctx.user_rating(RatingTrack, self.id)
        if rating is not None:
            info["userRating"] = rating

        avgRating = ctx.avg_rating(RatingTrack, self.id)
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
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        ret = f"{m:02}:{s:02}"
        if h:
            ret = f"{h:02}:{ret}"
        return ret

    def suffix(self):
        return os.path.splitext(self.path)[1][1:].lower()

    def sort_key(self):
        return f"{self.album.artist.name}{self.album.name}{self.disc:02}{self.number:02}{self.title}".lower()


class User(Model):
    id = PrimaryKeyField()
    name = CharField(64, unique=True)
    mail = CharField(null=True)
    password = CharField(256)

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


class ClientPrefs(Model):
    user = ForeignKeyField(User, backref="clients")
    client_name = CharField(32)
    format = CharField(8, null=True)
    bitrate = IntegerField(null=True)

    class Meta:
        primary_key = CompositeKey("user", "client_name")


def _make_starred_model(target_model):
    class Starred(Model):
        user = ForeignKeyField(User, backref="+")
        starred = ForeignKeyField(target_model, backref="+")
        date = DateTimeField(default=datetime.now)

        class Meta:
            primary_key = CompositeKey("user", "starred")
            table_name = "starred_" + target_model._meta.table_name

    return Starred


StarredFolder = _make_starred_model(Folder)
StarredArtist = _make_starred_model(Artist)
StarredAlbum = _make_starred_model(Album)
StarredTrack = _make_starred_model(Track)


def _make_rating_model(target_model):
    class Rating(Model):
        user = ForeignKeyField(User, backref="+")
        rated = ForeignKeyField(target_model, backref="+")
        rating = IntegerField()  # min=1, max=5

        class Meta:
            primary_key = CompositeKey("user", "rated")
            table_name = "rating_" + target_model._meta.table_name

    return Rating


RatingFolder = _make_rating_model(Folder)
RatingTrack = _make_rating_model(Track)


class ChatMessage(Model):
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


class Playlist(Model):
    id = PrimaryKeyField()
    user = ForeignKeyField(User, backref="playlists")
    name = CharField()
    comment = CharField(null=True)
    public = BooleanField(default=False)
    created = DateTimeField(default=datetime.now)

    def as_subsonic_playlist(self, user):
        tracks, duration = self.__tracks_query(
            fn.count("*"), fn.sum(Track.duration)
        ).scalar(as_tuple=True)
        info = {
            "id": str(self.id),
            "name": (
                self.name
                if self.user.id == user.id
                else f"[{self.user.name}] {self.name}"
            ),
            "owner": self.user.name,
            "public": self.public,
            "songCount": tracks,
            "duration": duration or 0,
            "created": self.created.isoformat(),
        }
        if self.comment:
            info["comment"] = self.comment
        return info

    def get_tracks(self):
        return [t for t in self.__tracks_query().order_by(PlaylistTrack.index)]

    def __tracks_query(self, *fields):
        return (
            Track.select(*fields)
            .join(PlaylistTrack)
            .where(PlaylistTrack.playlist == self)
        )

    def clear(self):
        PlaylistTrack.delete().where(PlaylistTrack.playlist == self).execute()

    def add(self, track):
        if isinstance(track, UUID):
            tid = track
        elif isinstance(track, Track):
            tid = track.id
        elif isinstance(track, str):
            tid = UUID(track)

        index = (
            PlaylistTrack.select(fn.max(PlaylistTrack.index))
            .where(PlaylistTrack.playlist == self)
            .scalar()
        )
        index = 0 if index is None else index + 1
        PlaylistTrack.create(playlist=self, track=tid, index=index)

    def remove_at_indexes(self, indexes):
        max_index, count = (
            PlaylistTrack.select(fn.max(PlaylistTrack.index), fn.count("*"))
            .where(PlaylistTrack.playlist == self)
            .scalar(as_tuple=True)
        )
        should_reindex = count != max_index + 1

        if should_reindex:
            query = (
                PlaylistTrack.select(PlaylistTrack.id)
                .where(PlaylistTrack.playlist == self)
                .order_by(PlaylistTrack.index)
            )
            for i, t in zip(range(count), query):
                t.index = i
                t.save(only=(PlaylistTrack.index,))

        for i in sorted(set(indexes), reverse=True):
            if i < 0:
                continue
            PlaylistTrack.delete().where(
                PlaylistTrack.playlist == self, PlaylistTrack.index == i
            ).execute()
            PlaylistTrack.update({PlaylistTrack.index: PlaylistTrack.index - 1}).where(
                PlaylistTrack.playlist == self, PlaylistTrack.index > i
            ).execute()


class PlaylistTrack(Model):
    id = PrimaryKeyField()
    playlist = ForeignKeyField(Playlist, backref="+")
    track = ForeignKeyField(Track, backref="+")
    index = IntegerField()


class RadioStation(Model):
    id = PrimaryKeyField()
    stream_url = CharField()
    name = CharField()
    homepage_url = CharField(null=True)
    created = DateTimeField(default=datetime.now)

    def as_subsonic_station(self):
        info = {
            "id": str(self.id),
            "streamUrl": self.stream_url,
            "name": self.name,
            "homePageUrl": self.homepage_url,
        }
        return info

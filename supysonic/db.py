# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import importlib
import importlib.resources
import mimetypes
import os.path
import time
from base64 import b64decode, b64encode
from datetime import datetime
from functools import cache
from hashlib import sha1
from os import urandom
from urllib.parse import urlparse
from uuid import UUID, uuid4

from peewee import (
    AutoField,
    BigIntegerField,
    BlobField,
    BooleanField,
    CharField,
    CompositeKey,
    DatabaseProxy,
    DateTimeField,
    FixedCharField,
    ForeignKeyField,
    IntegerField,
    Model,
    MySQLDatabase,
    UUIDField,
    fn,
)
from playhouse.db_url import parseresult_to_dict, schemes

from .pathutils import subpath_expr

SCHEMA_VERSION = "20260824"


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


class Artist(_Model):
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


class Album(_Model):
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
    size = BigIntegerField(default=0)

    path = CharField(4096)  # unique
    _path_hash = BlobField(column_name="path_hash", unique=True)
    created = DateTimeField(default=now)
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


class User(_Model):
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


class SerializationContext:
    """Per-request serialization state shared by the ``as_subsonic_*`` methods.

    Carries the two invariants of a single serialization: the ``user`` the
    response is built for and that user's ``ClientPrefs`` (``prefs``, used to
    advertise transcoding). It also batches the per-user annotations (starred /
    user-rating / average-rating) for a whole collection, collapsing what would
    be per-item lookups into one ``IN`` query per annotation: populate it with
    ``add_tracks`` / ``add_folders`` / ``add_artists`` / ``add_albums`` before
    serializing, then every ``as_subsonic_*`` call reads from it.

    Keys are normalized to ``str`` so int (Folder) and UUID (Track/Album/Artist)
    identifiers compare reliably regardless of the value Peewee returns for a
    raw foreign-key attribute.
    """

    def __init__(self, user, prefs=None):
        self.user = user
        self.prefs = prefs
        self._starred = {}  # (star_model, str(entity_id)) -> iso date str
        self._rating = {}  # (rating_model, str(entity_id)) -> int
        self._avg = {}  # (rating_model, str(entity_id)) -> float
        self._folder_cover = {}  # str(folder_id) -> coverArt id str
        self._album_agg = {}  # str(album_id) -> (duration, created, year, songCount)
        self._album_genre = {}  # str(album_id) -> [genre, ...]
        self._album_cover = {}  # str(album_id) -> coverArt id str
        self._artist_albums = {}  # str(artist_id) -> albumCount

    def _add_starred(self, star_model, ids):
        if not ids:
            return
        for s in star_model.select().where(
            star_model.user == self.user, star_model.starred.in_(ids)
        ):
            self._starred[(star_model, str(s.starred_id))] = s.date.isoformat()

    def _add_ratings(self, rating_model, ids):
        if not ids:
            return
        for r in rating_model.select().where(
            rating_model.user == self.user, rating_model.rated.in_(ids)
        ):
            self._rating[(rating_model, str(r.rated_id))] = r.rating
        for rated_id, avg in (
            rating_model.select(
                rating_model.rated, fn.avg(rating_model.rating, coerce=False)
            )
            .where(rating_model.rated.in_(ids))
            .group_by(rating_model.rated)
            .tuples()
        ):
            if avg:
                self._avg[(rating_model, str(rated_id))] = avg

    def add_tracks(self, tracks):
        tracks = list(tracks)
        ids = [t.id for t in tracks]
        self._add_starred(StarredTrack, ids)
        self._add_ratings(RatingTrack, ids)
        self._preload_track_fks(tracks)

    def add_folders(self, folders):
        folders = list(folders)
        ids = [f.id for f in folders]
        self._add_starred(StarredFolder, ids)
        self._add_ratings(RatingFolder, ids)
        self._preload_folder_parents(folders)
        self._preload_folder_covers(folders)

    def add_artists(self, artists):
        artists = list(artists)
        self._add_starred(StarredArtist, [a.id for a in artists])
        self._preload_artist_album_counts(artists)

    def add_albums(self, albums):
        albums = list(albums)
        self._add_starred(StarredAlbum, [a.id for a in albums])
        self._preload_album_artists(albums)
        self._preload_album_aggregates(albums)

    # Foreign-key preloading: batch-fetch the related rows a serializer will
    # dereference and assign them onto the instances, so accessing them issues
    # no per-row query. Callers that sort a collection by ``Track.sort_key`` (it
    # reads ``album.artist``) must ``add_tracks`` *before* sorting.
    def _preload_track_fks(self, tracks):
        if not tracks:
            return

        folder_ids = {t.folder_id for t in tracks} | {t.root_folder_id for t in tracks}
        folders = {f.id: f for f in Folder.select().where(Folder.id.in_(folder_ids))}
        albums = {
            a.id: a
            for a in Album.select().where(Album.id.in_({t.album_id for t in tracks}))
        }
        artist_ids = {t.artist_id for t in tracks} | {
            a.artist_id for a in albums.values()
        }
        artists = {a.id: a for a in Artist.select().where(Artist.id.in_(artist_ids))}
        for a in albums.values():
            a.artist = artists[a.artist_id]
        for t in tracks:
            t.folder = folders[t.folder_id]
            t.root_folder = folders[t.root_folder_id]
            t.album = albums[t.album_id]
            t.artist = artists[t.artist_id]

    def _preload_folder_parents(self, folders):
        parent_ids = {f.parent_id for f in folders if f.parent_id is not None}
        if not parent_ids:
            return

        parents = {f.id: f for f in Folder.select().where(Folder.id.in_(parent_ids))}
        for f in folders:
            if f.parent_id is not None:
                f.parent = parents[f.parent_id]

    def _preload_album_artists(self, albums):
        if not albums:
            return

        artist_ids = {a.artist_id for a in albums}
        artists = {a.id: a for a in Artist.select().where(Artist.id.in_(artist_ids))}
        for a in albums:
            a.artist = artists[a.artist_id]

    # Aggregate preloading: batch the per-item sub-aggregates the serializers
    # would otherwise compute one entity at a time (cover art scanned from a
    # folder's/album's tracks, album duration/count/genre/year, artist album
    # count). Each loader issues a fixed number of grouped queries for the whole
    # collection; the serializers then read the results by id.
    def _preload_folder_covers(self, folders):
        # Folders without their own cover_art advertise their first has-art track
        ids = [f.id for f in folders if not f.cover_art]
        if not ids:
            return

        for fid, tid in (
            Track.select(Track.folder, Track.id)
            .where(Track.folder.in_(ids), Track.has_art)
            .tuples()
        ):
            self._folder_cover.setdefault(str(fid), str(tid))

    def _preload_album_aggregates(self, albums):
        ids = [a.id for a in albums]
        if not ids:
            return

        for aid, duration, created, year, count in (
            Track.select(
                Track.album,
                fn.sum(Track.duration),
                fn.min(Track.created),
                fn.min(Track.year),
                fn.count("*"),
            )
            .where(Track.album.in_(ids))
            .group_by(Track.album)
            .tuples()
        ):
            self._album_agg[str(aid)] = (duration, created, year, count)

        for aid, genre in (
            Track.select(Track.album, Track.genre)
            .where(Track.album.in_(ids), Track.genre.is_null(False))
            .distinct()
            .tuples()
        ):
            self._album_genre.setdefault(str(aid), []).append(genre)

        # Cover art: prefer a track whose folder has cover art, else a track
        # with embedded art
        for aid, fid in (
            Track.select(Track.album, Folder.id)
            .join(Folder, on=Track.folder)
            .where(Track.album.in_(ids), Folder.cover_art.is_null(False))
            .tuples()
        ):
            self._album_cover.setdefault(str(aid), str(fid))

        remaining = [a.id for a in albums if str(a.id) not in self._album_cover]
        if remaining:
            for aid, tid in (
                Track.select(Track.album, Track.id)
                .where(Track.album.in_(remaining), Track.has_art)
                .tuples()
            ):
                self._album_cover.setdefault(str(aid), str(tid))

    def _preload_artist_album_counts(self, artists):
        ids = [a.id for a in artists]
        if not ids:
            return

        for artist_id, count in (
            Album.select(Album.artist, fn.count("*"))
            .where(Album.artist.in_(ids))
            .group_by(Album.artist)
            .tuples()
        ):
            self._artist_albums[str(artist_id)] = count

    def starred_date(self, star_model, entity_id):
        return self._starred.get((star_model, str(entity_id)))

    def user_rating(self, rating_model, entity_id):
        return self._rating.get((rating_model, str(entity_id)))

    def avg_rating(self, rating_model, entity_id):
        return self._avg.get((rating_model, str(entity_id)))

    def folder_cover(self, folder_id):
        return self._folder_cover.get(str(folder_id))

    def album_aggregate(self, album_id):
        return self._album_agg.get(str(album_id))

    def album_genre(self, album_id):
        return ", ".join(self._album_genre.get(str(album_id), ()))

    def album_cover(self, album_id):
        return self._album_cover.get(str(album_id))

    def album_sort_key(self, album):
        agg = self._album_agg.get(str(album.id))
        year = (agg[2] if agg else None) or 9999
        return f"{year}{album.name.lower()}"

    def artist_album_count(self, artist_id):
        return self._artist_albums.get(str(artist_id), 0)


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


class PlaylistTrack(_Model):
    id = PrimaryKeyField()
    playlist = ForeignKeyField(Playlist, backref="+")
    track = ForeignKeyField(Track, backref="+")
    index = IntegerField()


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


def get_resource_text(respath):
    return importlib.resources.files(__package__).joinpath(respath).read_text("utf-8")


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
        provider = "mysql"
        args.setdefault("charset", "utf8mb4")
        args.setdefault("binary_prefix", True)
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


@cache
def get_secret_key(keyname):
    with db.atomic():
        m, created = Meta.get_or_create(key=keyname, defaults={"value": ""})
        if created:
            key = urandom(128)
            m.value = b64encode(key)
            m.save()
        else:
            key = b64decode(m.value)

    return key

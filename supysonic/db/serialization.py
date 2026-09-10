# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from peewee import fn

from .models import (
    Album,
    Artist,
    Folder,
    RatingFolder,
    RatingTrack,
    StarredAlbum,
    StarredArtist,
    StarredFolder,
    StarredTrack,
    Track,
)


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

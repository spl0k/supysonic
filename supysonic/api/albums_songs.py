# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from datetime import timedelta

from flask import request
from peewee import JOIN, fn

from ..db import (
    Album,
    Artist,
    Folder,
    RatingFolder,
    SerializationContext,
    StarredAlbum,
    StarredArtist,
    StarredFolder,
    StarredTrack,
    Track,
    User,
    now,
    random,
)
from ..pathutils import subpath_expr
from . import MAX_LIST_SIZE, api_routing, get_int, get_music_folder, get_paging
from .exceptions import GenericError


def _year_range():
    """Read the required fromYear/toYear pair of the 'byYear' album lists.

    Returns a (low, high, descending) tuple: Subsonic reverses the ordering when
    toYear is before fromYear.
    """
    startyear = get_int("fromYear", required=True)
    endyear = get_int("toYear", required=True)
    return min(startyear, endyear), max(startyear, endyear), endyear < startyear


@api_routing("/getRandomSongs")
def rand_songs():
    genre = request.values.get("genre")
    size = get_int("size", 10, min=0, max=MAX_LIST_SIZE)
    fromYear = get_int("fromYear")
    toYear = get_int("toYear")
    root = get_music_folder()

    query = Track.select()
    if fromYear:
        query = query.where(Track.year >= fromYear)
    if toYear:
        query = query.where(Track.year <= toYear)
    if genre:
        query = query.where(Track.genre == genre)
    if root:
        query = query.where(Track.root_folder == root)

    tracks = list(query.order_by(random()).limit(size))
    ctx = SerializationContext(request.user, request.client)
    ctx.add_tracks(tracks)

    return request.formatter(
        "randomSongs",
        {"song": [t.as_subsonic_child(ctx) for t in tracks]},
    )


@api_routing("/getAlbumList")
def album_list():
    ltype = request.values["type"]

    size, offset = get_paging("size", default=10)
    root = get_music_folder()

    query = Folder.select().join(Track, on=Track.folder).switch().group_by(Folder.id)
    if root is not None:
        query = query.where(Track.root_folder == root)

    if ltype == "random":
        # Paging a random ordering is meaningless, offset is ignored
        query = query.order_by(random())
        offset = 0
    # Folder.id is always appended to the ordering: the sort keys below aren't
    # unique, and without a tiebreaker paging could skip or repeat albums.
    elif ltype == "newest":
        query = query.order_by(Folder.created.desc(), Folder.id)
    elif ltype == "highest":
        query = query.join(RatingFolder, JOIN.LEFT_OUTER).order_by(
            fn.avg(RatingFolder.rating).desc(), Folder.id
        )
    elif ltype == "frequent":
        query = query.order_by(fn.avg(Track.play_count).desc(), Folder.id)
    elif ltype == "recent":
        query = query.where(Track.last_play.is_null(False)).order_by(
            fn.max(Track.last_play).desc(), Folder.id
        )
    elif ltype == "starred":
        query = (
            query.join(StarredFolder)
            .where(StarredFolder.user == request.user)
            .order_by(Folder.name, Folder.id)
        )
    elif ltype == "alphabeticalByName":
        query = query.order_by(Folder.name, Folder.id)
    elif ltype == "alphabeticalByArtist":
        parent = Folder.alias()
        query = (
            query.join(parent)
            .group_by_extend(parent.id)
            .order_by(parent.name, Folder.name, Folder.id)
        )
    elif ltype == "byYear":
        low, high, descending = _year_range()
        query = query.where(Track.year.between(low, high))
        order = fn.min(Track.year)
        if descending:
            order = order.desc()
        query = query.order_by(order, Folder.id)
    elif ltype == "byGenre":
        genre = request.values["genre"]
        query = query.where(Track.genre == genre).order_by(Folder.name, Folder.id)
    else:
        raise GenericError("Unknown search type")

    folders = list(query.limit(size).offset(offset))
    ctx = SerializationContext(request.user, request.client)
    ctx.add_folders(folders)
    return request.formatter(
        "albumList",
        {"album": [f.as_subsonic_child(ctx) for f in folders]},
    )


@api_routing("/getAlbumList2")
def album_list_id3():
    ltype = request.values["type"]

    size, offset = get_paging("size", default=10)
    root = get_music_folder()

    query = Album.select().join(Track).group_by(Album.id)
    if root is not None:
        query = query.where(Track.root_folder == root)

    if ltype == "random":
        # Paging a random ordering is meaningless, offset is ignored
        query = query.order_by(random())
        offset = 0
    # See getAlbumList: Album.id is appended as a tiebreaker for stable paging.
    elif ltype == "newest":
        query = query.order_by(fn.min(Track.created).desc(), Album.id)
    elif ltype == "frequent":
        query = query.order_by(fn.avg(Track.play_count).desc(), Album.id)
    elif ltype == "recent":
        query = query.where(Track.last_play.is_null(False)).order_by(
            fn.max(Track.last_play).desc(), Album.id
        )
    elif ltype == "starred":
        query = (
            query.switch()
            .join(StarredAlbum)
            .where(StarredAlbum.user == request.user)
            .order_by(Album.name, Album.id)
        )
    elif ltype == "alphabeticalByName":
        query = query.order_by(Album.name, Album.id)
    elif ltype == "alphabeticalByArtist":
        query = (
            query.switch()
            .join(Artist)
            .group_by_extend(Artist.id)
            .order_by(Artist.name, Album.name, Album.id)
        )
    elif ltype == "byYear":
        low, high, descending = _year_range()
        query = query.having(fn.min(Track.year).between(low, high))
        order = fn.min(Track.year)
        if descending:
            order = order.desc()
        query = query.order_by(order, Album.id)
    elif ltype == "byGenre":
        genre = request.values["genre"]
        query = query.where(Track.genre == genre).order_by(Album.name, Album.id)
    else:
        raise GenericError("Unknown search type")

    albums = list(query.limit(size).offset(offset))
    ctx = SerializationContext(request.user, request.client)
    ctx.add_albums(albums)
    return request.formatter(
        "albumList2",
        {"album": [a.as_subsonic_album(ctx) for a in albums]},
    )


@api_routing("/getSongsByGenre")
def songs_by_genre():
    genre = request.values["genre"]

    count, offset = get_paging("count", default=10)
    root = get_music_folder()

    # Joins are many-to-one, they don't duplicate rows. Ordering mirrors
    # Track.sort_key, with the primary key as a tiebreaker so paging is stable.
    query = (
        Track.select()
        .join(Album)
        .join(Artist)
        .switch(Track)
        .where(Track.genre == genre)
        .order_by(
            Artist.name, Album.name, Track.disc, Track.number, Track.title, Track.id
        )
    )
    if root is not None:
        query = query.where(Track.root_folder == root)

    tracks = list(query.limit(count).offset(offset))
    ctx = SerializationContext(request.user, request.client)
    ctx.add_tracks(tracks)
    return request.formatter(
        "songsByGenre",
        {"song": [t.as_subsonic_child(ctx) for t in tracks]},
    )


@api_routing("/getNowPlaying")
def now_playing():
    query = (
        User.select(User, Track)
        .join(Track, on=User.last_play)
        .where(
            User.last_play.is_null(False),
            User.last_play_date > now() - timedelta(minutes=3),
        )
    )

    users = list(query)
    ctx = SerializationContext(request.user, request.client)
    ctx.add_tracks([u.last_play for u in users])

    return request.formatter(
        "nowPlaying",
        {
            "entry": [
                {
                    **u.last_play.as_subsonic_child(ctx),
                    "username": u.name,
                    "minutesAgo": (now() - u.last_play_date).seconds // 60,
                    "playerId": 0,
                }
                for u in users
            ]
        },
    )


@api_routing("/getStarred")
def get_starred():
    root = get_music_folder()

    folders = (
        StarredFolder.select(StarredFolder.starred, Folder)
        .join(Folder)
        .join(Track, on=Track.folder)
        .where(StarredFolder.user == request.user)
        .group_by(StarredFolder.starred, Folder)
    )
    if root is not None:
        folders = folders.where(subpath_expr(Folder.path, root.path))

    arq = folders.having(fn.count(Track.id) == 0)
    alq = folders.having(fn.count(Track.id) > 0)
    trq = (
        StarredTrack.select(StarredTrack.starred, Track)
        .join(Track)
        .where(StarredTrack.user == request.user)
    )

    if root is not None:
        trq = trq.where(Track.root_folder == root)

    artist_folders = [sf.starred for sf in arq]
    album_folders = [sf.starred for sf in alq]
    tracks = [st.starred for st in trq]

    ctx = SerializationContext(request.user, request.client)
    ctx.add_folders(artist_folders + album_folders)
    ctx.add_tracks(tracks)

    return request.formatter(
        "starred",
        {
            "artist": [f.as_subsonic_artist(ctx) for f in artist_folders],
            "album": [f.as_subsonic_child(ctx) for f in album_folders],
            "song": [t.as_subsonic_child(ctx) for t in tracks],
        },
    )


@api_routing("/getStarred2")
def get_starred_id3():
    root = get_music_folder()

    arq = (
        StarredArtist.select(StarredArtist.starred, Artist)
        .join(Artist)
        .where(StarredArtist.user == request.user)
    )
    alq = (
        StarredAlbum.select(StarredAlbum.starred, Album)
        .join(Album)
        .where(StarredAlbum.user == request.user)
    )
    trq = (
        StarredTrack.select(StarredTrack.starred, Track)
        .join(Track)
        .where(StarredTrack.user == request.user)
    )

    if root is not None:
        arq = arq.join(Track).where(Track.root_folder == root)
        alq = alq.join(Track).where(Track.root_folder == root)
        trq = trq.where(Track.root_folder == root)

    artists = [sa.starred for sa in arq]
    albums = [sa.starred for sa in alq]
    tracks = [st.starred for st in trq]

    ctx = SerializationContext(request.user, request.client)
    ctx.add_artists(artists)
    ctx.add_albums(albums)
    ctx.add_tracks(tracks)

    return request.formatter(
        "starred2",
        {
            "artist": [a.as_subsonic_artist(ctx) for a in artists],
            "album": [a.as_subsonic_album(ctx) for a in albums],
            "song": [t.as_subsonic_child(ctx) for t in tracks],
        },
    )

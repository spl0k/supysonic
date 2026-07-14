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
from . import api_routing, get_root_folder
from .exceptions import GenericError


@api_routing("/getRandomSongs")
def rand_songs():
    size = request.values.get("size", "10")
    genre, fromYear, toYear, musicFolderId = map(
        request.values.get, ("genre", "fromYear", "toYear", "musicFolderId")
    )

    size = int(size) if size else 10
    fromYear = int(fromYear) if fromYear else None
    toYear = int(toYear) if toYear else None
    root = get_root_folder(musicFolderId)

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

    size, offset, mfid = map(request.values.get, ("size", "offset", "musicFolderId"))
    size = int(size) if size else 10
    offset = int(offset) if offset else 0
    root = get_root_folder(mfid)

    query = Folder.select().join(Track, on=Track.folder).switch().group_by(Folder.id)
    if root is not None:
        query = query.where(Track.root_folder == root)

    if ltype == "random":
        folders = list(query.order_by(random()).limit(size))
        ctx = SerializationContext(request.user, request.client)
        ctx.add_folders(folders)
        return request.formatter(
            "albumList",
            {"album": [f.as_subsonic_child(ctx) for f in folders]},
        )
    elif ltype == "newest":
        query = query.order_by(Folder.created.desc())
    elif ltype == "highest":
        query = query.join(RatingFolder, JOIN.LEFT_OUTER).order_by(
            fn.avg(RatingFolder.rating).desc()
        )
    elif ltype == "frequent":
        query = query.order_by(fn.avg(Track.play_count).desc())
    elif ltype == "recent":
        query = query.where(Track.last_play.is_null(False)).order_by(
            fn.max(Track.last_play).desc()
        )
    elif ltype == "starred":
        query = query.join(StarredFolder).where(StarredFolder.user == request.user)
    elif ltype == "alphabeticalByName":
        query = query.order_by(Folder.name)
    elif ltype == "alphabeticalByArtist":
        parent = Folder.alias()
        query = (
            query.join(parent)
            .group_by_extend(parent.id)
            .order_by(parent.name, Folder.name)
        )
    elif ltype == "byYear":
        startyear = int(request.values["fromYear"])
        endyear = int(request.values["toYear"])
        query = query.where(
            Track.year.between(min(startyear, endyear), max(startyear, endyear))
        )
        order = fn.min(Track.year)
        if endyear < startyear:
            order = order.desc()
        query = query.order_by(order)
    elif ltype == "byGenre":
        genre = request.values["genre"]
        query = query.where(Track.genre == genre)
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

    size, offset, mfid = map(request.values.get, ("size", "offset", "musicFolderId"))
    size = int(size) if size else 10
    offset = int(offset) if offset else 0
    root = get_root_folder(mfid)

    query = Album.select().join(Track).group_by(Album.id)
    if root is not None:
        query = query.where(Track.root_folder == root)

    if ltype == "random":
        albums = list(query.order_by(random()).limit(size))
        ctx = SerializationContext(request.user, request.client)
        ctx.add_albums(albums)
        return request.formatter(
            "albumList2",
            {"album": [a.as_subsonic_album(ctx) for a in albums]},
        )
    elif ltype == "newest":
        query = query.order_by(fn.min(Track.created).desc())
    elif ltype == "frequent":
        query = query.order_by(fn.avg(Track.play_count).desc())
    elif ltype == "recent":
        query = query.where(Track.last_play.is_null(False)).order_by(
            fn.max(Track.last_play).desc()
        )
    elif ltype == "starred":
        query = (
            query.switch().join(StarredAlbum).where(StarredAlbum.user == request.user)
        )
    elif ltype == "alphabeticalByName":
        query = query.order_by(Album.name)
    elif ltype == "alphabeticalByArtist":
        query = (
            query.switch()
            .join(Artist)
            .group_by_extend(Artist.id)
            .order_by(Artist.name, Album.name)
        )
    elif ltype == "byYear":
        startyear = int(request.values["fromYear"])
        endyear = int(request.values["toYear"])
        query = query.having(
            fn.min(Track.year).between(min(startyear, endyear), max(startyear, endyear))
        )
        order = fn.min(Track.year)
        if endyear < startyear:
            order = order.desc()
        query = query.order_by(order)
    elif ltype == "byGenre":
        genre = request.values["genre"]
        query = query.where(Track.genre == genre)
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

    count, offset, mfid = map(request.values.get, ("count", "offset", "musicFolderId"))
    count = int(count) if count else 10
    offset = int(offset) if offset else 0
    root = get_root_folder(mfid)

    query = Track.select().where(Track.genre == genre)
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
    query = User.select().where(
        User.last_play.is_null(False),
        User.last_play_date > now() - timedelta(minutes=3),
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
    mfid = request.values.get("musicFolderId")
    root = get_root_folder(mfid)

    folders = (
        StarredFolder.select(StarredFolder.starred)
        .join(Folder)
        .join(Track, on=Track.folder)
        .where(StarredFolder.user == request.user)
        .group_by(StarredFolder.starred)
    )
    if root is not None:
        folders = folders.where(Folder.path.startswith(root.path))

    arq = folders.having(fn.count(Track.id) == 0)
    alq = folders.having(fn.count(Track.id) > 0)
    trq = (
        StarredTrack.select(StarredTrack.starred)
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
    mfid = request.values.get("musicFolderId")
    root = get_root_folder(mfid)

    arq = (
        StarredArtist.select(StarredArtist.starred)
        .join(Artist)
        .where(StarredArtist.user == request.user)
    )
    alq = (
        StarredAlbum.select(StarredAlbum.starred)
        .join(Album)
        .where(StarredAlbum.user == request.user)
    )
    trq = (
        StarredTrack.select(StarredTrack.starred)
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

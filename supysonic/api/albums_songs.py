# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from datetime import timedelta
from flask import request
from pony.orm import select, desc, avg, max, min, count, between, distinct

from ..db import (
    Folder,
    Album,
    Track,
    StarredFolder,
    StarredArtist,
    StarredAlbum,
    StarredTrack,
    User,
)
from ..db import now

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
        query = query.filter(lambda t: t.year >= fromYear)
    if toYear:
        query = query.filter(lambda t: t.year <= toYear)
    if genre:
        query = query.filter(lambda t: t.genre == genre)
    if root:
        query = query.filter(lambda t: t.root_folder == root)

    return request.formatter(
        "randomSongs",
        {
            "song": [
                t.as_subsonic_child(request.user, request.client)
                for t in query.without_distinct().random(size)
            ]
        },
    )


@api_routing("/getAlbumList")
def album_list():
    ltype = request.values["type"]

    size, offset, mfid = map(request.values.get, ("size", "offset", "musicFolderId"))
    size = int(size) if size else 10
    offset = int(offset) if offset else 0
    root = get_root_folder(mfid)

    query = select(t.folder for t in Track)
    if root is not None:
        query = select(t.folder for t in Track if t.root_folder == root)

    if ltype == "random":
        return request.formatter(
            "albumList",
            {
                "album": [
                    a.as_subsonic_child(request.user)
                    for a in distinct(query.random(size))
                ]
            },
        )
    elif ltype == "newest":
        query = query.sort_by(desc(Folder.created)).distinct()
    elif ltype == "highest":
        query = query.sort_by(lambda f: desc(avg(f.ratings.rating)))
    elif ltype == "frequent":
        query = query.sort_by(lambda f: desc(avg(f.tracks.play_count)))
    elif ltype == "recent":
        query = select(
            t.folder for t in Track if max(t.folder.tracks.last_play) is not None
        )
        if root is not None:
            query = query.where(lambda t: t.root_folder == root)
        query = query.sort_by(lambda f: desc(max(f.tracks.last_play)))
    elif ltype == "starred":
        query = select(
            s.starred
            for s in StarredFolder
            if s.user.id == request.user.id and count(s.starred.tracks) > 0
        )
        if root is not None:
            query = query.filter(lambda f: f.path.startswith(root.path))
    elif ltype == "alphabeticalByName":
        query = query.sort_by(Folder.name).distinct()
    elif ltype == "alphabeticalByArtist":
        query = query.sort_by(lambda f: f.parent.name + f.name)
    elif ltype == "byYear":
        startyear = int(request.values["fromYear"])
        endyear = int(request.values["toYear"])
        query = query.where(
            lambda t: between(t.year, min(startyear, endyear), max(startyear, endyear))
        )
        if endyear < startyear:
            query = query.sort_by(lambda f: desc(min(f.tracks.year)))
        else:
            query = query.sort_by(lambda f: min(f.tracks.year))
    elif ltype == "byGenre":
        genre = request.values["genre"]
        query = query.where(lambda t: t.genre == genre)
    else:
        raise GenericError("Unknown search type")

    return request.formatter(
        "albumList",
        {
            "album": [
                f.as_subsonic_child(request.user) for f in query.limit(size, offset)
            ]
        },
    )


@api_routing("/getAlbumList2")
def album_list_id3():
    ltype = request.values["type"]

    size, offset, mfid = map(request.values.get, ("size", "offset", "musicFolderId"))
    size = int(size) if size else 10
    offset = int(offset) if offset else 0
    root = get_root_folder(mfid)

    query = Album.select()
    if root is not None:
        query = query.where(lambda a: root in a.tracks.root_folder)

    if ltype == "random":
        return request.formatter(
            "albumList2",
            {"album": [a.as_subsonic_album(request.user) for a in query.random(size)]},
        )
    elif ltype == "newest":
        query = query.order_by(lambda a: desc(min(a.tracks.created)))
    elif ltype == "frequent":
        query = query.order_by(lambda a: desc(avg(a.tracks.play_count)))
    elif ltype == "recent":
        query = query.where(lambda a: max(a.tracks.last_play) is not None).order_by(
            lambda a: desc(max(a.tracks.last_play))
        )
    elif ltype == "starred":
        query = select(s.starred for s in StarredAlbum if s.user.id == request.user.id)
        if root is not None:
            query = query.filter(lambda a: root in a.tracks.root_folder)
    elif ltype == "alphabeticalByName":
        query = query.order_by(Album.name)
    elif ltype == "alphabeticalByArtist":
        query = query.order_by(lambda a: a.artist.name + a.name)
    elif ltype == "byYear":
        startyear = int(request.values["fromYear"])
        endyear = int(request.values["toYear"])
        query = query.where(
            lambda a: between(
                min(a.tracks.year), min(startyear, endyear), max(startyear, endyear)
            )
        )
        if endyear < startyear:
            query = query.order_by(lambda a: desc(min(a.tracks.year)))
        else:
            query = query.order_by(lambda a: min(a.tracks.year))
    elif ltype == "byGenre":
        genre = request.values["genre"]
        query = query.where(lambda a: genre in a.tracks.genre)
    else:
        raise GenericError("Unknown search type")

    return request.formatter(
        "albumList2",
        {
            "album": [
                f.as_subsonic_album(request.user) for f in query.limit(size, offset)
            ]
        },
    )


@api_routing("/getSongsByGenre")
def songs_by_genre():
    genre = request.values["genre"]

    count, offset, mfid = map(request.values.get, ("count", "offset", "musicFolderId"))
    count = int(count) if count else 10
    offset = int(offset) if offset else 0
    root = get_root_folder(mfid)

    query = select(t for t in Track if t.genre == genre)
    if root is not None:
        query = query.where(lambda t: t.root_folder == root)
    return request.formatter(
        "songsByGenre",
        {
            "song": [
                t.as_subsonic_child(request.user, request.client)
                for t in query.limit(count, offset)
            ]
        },
    )


@api_routing("/getNowPlaying")
def now_playing():
    query = User.select(
        lambda u: u.last_play is not None
        and u.last_play_date + timedelta(minutes=3) > now()
    )

    return request.formatter(
        "nowPlaying",
        {
            "entry": [
                {
                    **u.last_play.as_subsonic_child(request.user, request.client),
                    "username": u.name,
                    "minutesAgo": (now() - u.last_play_date).seconds / 60,
                    "playerId": 0,
                }
                for u in query
            ]
        },
    )


@api_routing("/getStarred")
def get_starred():
    mfid = request.values.get("musicFolderId")
    root = get_root_folder(mfid)

    folders = select(s.starred for s in StarredFolder if s.user.id == request.user.id)
    if root is not None:
        folders = folders.filter(lambda f: f.path.startswith(root.path))

    arq = folders.filter(lambda f: count(f.tracks) == 0)
    alq = folders.filter(lambda f: count(f.tracks) > 0)
    trq = select(s.starred for s in StarredTrack if s.user.id == request.user.id)

    if root is not None:
        trq = trq.filter(lambda t: t.root_folder == root)

    return request.formatter(
        "starred",
        {
            "artist": [sf.as_subsonic_artist(request.user) for sf in arq],
            "album": [sf.as_subsonic_child(request.user) for sf in alq],
            "song": [st.as_subsonic_child(request.user, request.client) for st in trq],
        },
    )


@api_routing("/getStarred2")
def get_starred_id3():
    mfid = request.values.get("musicFolderId")
    root = get_root_folder(mfid)

    arq = select(s.starred for s in StarredArtist if s.user.id == request.user.id)
    alq = select(s.starred for s in StarredAlbum if s.user.id == request.user.id)
    trq = select(s.starred for s in StarredTrack if s.user.id == request.user.id)

    if root is not None:
        arq = arq.filter(lambda a: root in a.tracks.root_folder)
        alq = alq.filter(lambda a: root in a.tracks.root_folder)
        trq = trq.filter(lambda t: t.root_folder == root)

    return request.formatter(
        "starred2",
        {
            "artist": [sa.as_subsonic_artist(request.user) for sa in arq],
            "album": [sa.as_subsonic_album(request.user) for sa in alq],
            "song": [st.as_subsonic_child(request.user, request.client) for st in trq],
        },
    )

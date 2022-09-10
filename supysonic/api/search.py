# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from collections import OrderedDict
from datetime import datetime
from flask import request
from pony.orm import select

from ..db import Folder, Track, Artist, Album

from . import api_routing, get_root_folder
from .exceptions import MissingParameter


@api_routing("/search")
def old_search():
    artist, album, title, anyf, count, offset, newer_than = map(
        request.values.get,
        ("artist", "album", "title", "any", "count", "offset", "newerThan"),
    )

    count = int(count) if count else 20
    offset = int(offset) if offset else 0
    newer_than = int(newer_than) / 1000 if newer_than else 0
    min_date = datetime.fromtimestamp(newer_than)

    if artist:
        query = select(
            t.folder.parent
            for t in Track
            if artist in t.folder.parent.name and t.folder.parent.created > min_date
        )
    elif album:
        query = select(
            t.folder
            for t in Track
            if album in t.folder.name and t.folder.created > min_date
        )
    elif title:
        query = Track.select(lambda t: title in t.title and t.created > min_date)
    elif anyf:
        folders = Folder.select(lambda f: anyf in f.name and f.created > min_date)
        tracks = Track.select(lambda t: anyf in t.title and t.created > min_date)
        res = folders[offset : offset + count]
        fcount = folders.count()
        if offset + count > fcount:
            toff = max(0, offset - fcount)
            tend = offset + count - fcount
            res = res[:] + tracks[toff:tend][:]

        return request.formatter(
            "searchResult",
            {
                "totalHits": folders.count() + tracks.count(),
                "offset": offset,
                "match": [
                    r.as_subsonic_child(request.user)
                    if isinstance(r, Folder)
                    else r.as_subsonic_child(request.user, request.client)
                    for r in res
                ],
            },
        )
    else:
        raise MissingParameter("search")

    return request.formatter(
        "searchResult",
        {
            "totalHits": query.count(),
            "offset": offset,
            "match": [
                r.as_subsonic_child(request.user)
                if isinstance(r, Folder)
                else r.as_subsonic_child(request.user, request.client)
                for r in query[offset : offset + count]
            ],
        },
    )


@api_routing("/search2")
def new_search():
    query = request.values["query"]
    (
        artist_count,
        artist_offset,
        album_count,
        album_offset,
        song_count,
        song_offset,
        mfid,
    ) = map(
        request.values.get,
        (
            "artistCount",
            "artistOffset",
            "albumCount",
            "albumOffset",
            "songCount",
            "songOffset",
            "musicFolderId",
        ),
    )

    artist_count = int(artist_count) if artist_count else 20
    artist_offset = int(artist_offset) if artist_offset else 0
    album_count = int(album_count) if album_count else 20
    album_offset = int(album_offset) if album_offset else 0
    song_count = int(song_count) if song_count else 20
    song_offset = int(song_offset) if song_offset else 0
    root = get_root_folder(mfid)

    artists = select(t.folder.parent for t in Track if query in t.folder.parent.name)
    albums = select(t.folder for t in Track if query in t.folder.name)
    songs = Track.select(lambda t: query in t.title)

    if root is not None:
        artists = artists.where(lambda t: t.root_folder == root)
        albums = albums.where(lambda t: t.root_folder == root)
        songs = songs.where(lambda t: t.root_folder == root)

    artists = artists.limit(artist_count, artist_offset)
    albums = albums.limit(album_count, album_offset)
    songs = songs.limit(song_count, song_offset)

    return request.formatter(
        "searchResult2",
        OrderedDict(
            (
                ("artist", [a.as_subsonic_artist(request.user) for a in artists]),
                ("album", [f.as_subsonic_child(request.user) for f in albums]),
                (
                    "song",
                    [t.as_subsonic_child(request.user, request.client) for t in songs],
                ),
            )
        ),
    )


@api_routing("/search3")
def search_id3():
    query = request.values["query"]
    (
        artist_count,
        artist_offset,
        album_count,
        album_offset,
        song_count,
        song_offset,
        mfid,
    ) = map(
        request.values.get,
        (
            "artistCount",
            "artistOffset",
            "albumCount",
            "albumOffset",
            "songCount",
            "songOffset",
            "musicFolderId",
        ),
    )

    artist_count = int(artist_count) if artist_count else 20
    artist_offset = int(artist_offset) if artist_offset else 0
    album_count = int(album_count) if album_count else 20
    album_offset = int(album_offset) if album_offset else 0
    song_count = int(song_count) if song_count else 20
    song_offset = int(song_offset) if song_offset else 0
    root = get_root_folder(mfid)

    artists = Artist.select(lambda a: query in a.name)
    albums = Album.select(lambda a: query in a.name)
    songs = Track.select(lambda t: query in t.title)

    if root is not None:
        artists = artists.where(lambda a: root in a.tracks.root_folder)
        albums = albums.where(lambda a: root in a.tracks.root_folder)
        songs = songs.where(lambda t: t.root_folder == root)

    artists = artists.limit(artist_count, artist_offset)
    albums = albums.limit(album_count, album_offset)
    songs = songs.limit(song_count, song_offset)

    return request.formatter(
        "searchResult3",
        OrderedDict(
            (
                ("artist", [a.as_subsonic_artist(request.user) for a in artists]),
                ("album", [a.as_subsonic_album(request.user) for a in albums]),
                (
                    "song",
                    [t.as_subsonic_child(request.user, request.client) for t in songs],
                ),
            )
        ),
    )

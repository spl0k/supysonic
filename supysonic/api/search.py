# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from collections import OrderedDict
from datetime import datetime

from flask import request

from ..db import Album, Artist, Folder, SerializationContext, Track
from . import (
    MAX_LIST_SIZE,
    MAX_TIMESTAMP_MS,
    api_routing,
    get_int,
    get_root_folder,
)
from .exceptions import MissingParameter


def _match_list(items):
    """Serialize a mixed list of Folders/Tracks for the legacy search result,
    batching annotations through a shared context."""
    ctx = SerializationContext(request.user, request.client)
    ctx.add_folders([i for i in items if isinstance(i, Folder)])
    ctx.add_tracks([i for i in items if isinstance(i, Track)])
    return [
        (
            r.as_subsonic_child(ctx)
            if isinstance(r, Folder)
            else r.as_subsonic_child(ctx)
        )
        for r in items
    ]


@api_routing("/search")
def old_search():
    artist, album, title, anyf = map(
        request.values.get, ("artist", "album", "title", "any")
    )

    count = get_int("count", 20, min=0, max=MAX_LIST_SIZE)
    offset = get_int("offset", 0, min=0)
    newer_than = get_int("newerThan", 0, min=0, max=MAX_TIMESTAMP_MS)
    min_date = datetime.fromtimestamp(newer_than / 1000)

    if artist:
        Child = Folder.alias()
        query = (
            Folder.select()
            .join(Child, on=Child.parent == Folder.id)
            .join(Track, on=Track.folder == Child.id)
            .where(Folder.name.contains(artist), Folder.created > min_date)
            .distinct()
            .order_by(Folder.name, Folder.id)
        )
    elif album:
        query = (
            Folder.select()
            .join(Track, on=Track.folder)
            .where(Folder.name.contains(album), Folder.created > min_date)
            .distinct()
            .order_by(Folder.name, Folder.id)
        )
    elif title:
        query = (
            Track.select()
            .where(Track.title.contains(title), Track.created > min_date)
            .order_by(Track.title, Track.id)
        )
    elif anyf:
        folders = (
            Folder.select()
            .where(Folder.name.contains(anyf), Folder.created > min_date)
            .order_by(Folder.name, Folder.id)
        )
        tracks = (
            Track.select()
            .where(Track.title.contains(anyf), Track.created > min_date)
            .order_by(Track.title, Track.id)
        )
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
                "match": _match_list(res),
            },
        )
    else:
        raise MissingParameter("search")

    return request.formatter(
        "searchResult",
        {
            "totalHits": query.count(),
            "offset": offset,
            "match": _match_list(list(query[offset : offset + count])),
        },
    )


@api_routing("/search2")
def new_search():
    query = request.values["query"]

    artist_count = get_int("artistCount", 20, min=0, max=MAX_LIST_SIZE)
    artist_offset = get_int("artistOffset", 0, min=0)
    album_count = get_int("albumCount", 20, min=0, max=MAX_LIST_SIZE)
    album_offset = get_int("albumOffset", 0, min=0)
    song_count = get_int("songCount", 20, min=0, max=MAX_LIST_SIZE)
    song_offset = get_int("songOffset", 0, min=0)
    root = get_root_folder(request.values.get("musicFolderId"))

    Child = Folder.alias()
    artists = (
        Folder.select()
        .join(Child, on=Child.parent == Folder.id)
        .join(Track, on=Track.folder == Child.id)
        .where(Folder.name.contains(query))
        .distinct()
    )
    albums = (
        Folder.select()
        .join(Track, on=Track.folder)
        .where(Folder.name.contains(query))
        .distinct()
    )
    songs = Track.select().where(Track.title.contains(query))

    if root is not None:
        artists = artists.where(Track.root_folder == root)
        albums = albums.where(Track.root_folder == root)
        songs = songs.where(Track.root_folder == root)

    artists = list(
        artists.order_by(Folder.name, Folder.id)
        .limit(artist_count)
        .offset(artist_offset)
    )
    albums = list(
        albums.order_by(Folder.name, Folder.id).limit(album_count).offset(album_offset)
    )
    songs = list(
        songs.order_by(Track.title, Track.id).limit(song_count).offset(song_offset)
    )

    ctx = SerializationContext(request.user, request.client)
    ctx.add_folders(artists + albums)
    ctx.add_tracks(songs)

    return request.formatter(
        "searchResult2",
        OrderedDict(
            (
                ("artist", [a.as_subsonic_artist(ctx) for a in artists]),
                ("album", [f.as_subsonic_child(ctx) for f in albums]),
                (
                    "song",
                    [t.as_subsonic_child(ctx) for t in songs],
                ),
            )
        ),
    )


@api_routing("/search3")
def search_id3():
    query = request.values["query"]

    artist_count = get_int("artistCount", 20, min=0, max=MAX_LIST_SIZE)
    artist_offset = get_int("artistOffset", 0, min=0)
    album_count = get_int("albumCount", 20, min=0, max=MAX_LIST_SIZE)
    album_offset = get_int("albumOffset", 0, min=0)
    song_count = get_int("songCount", 20, min=0, max=MAX_LIST_SIZE)
    song_offset = get_int("songOffset", 0, min=0)
    root = get_root_folder(request.values.get("musicFolderId"))

    artists = Artist.select().where(Artist.name.contains(query))
    albums = Album.select().where(Album.name.contains(query))
    songs = Track.select().where(Track.title.contains(query))

    if root is not None:
        # distinct: the join is one row per track, without it an artist or album
        # would be repeated once per matching track
        artists = artists.join(Track).where(Track.root_folder == root).distinct()
        albums = albums.join(Track).where(Track.root_folder == root).distinct()
        songs = songs.where(Track.root_folder == root)

    artists = list(
        artists.order_by(Artist.name, Artist.id)
        .limit(artist_count)
        .offset(artist_offset)
    )
    albums = list(
        albums.order_by(Album.name, Album.id).limit(album_count).offset(album_offset)
    )
    songs = list(
        songs.order_by(Track.title, Track.id).limit(song_count).offset(song_offset)
    )

    ctx = SerializationContext(request.user, request.client)
    ctx.add_artists(artists)
    ctx.add_albums(albums)
    ctx.add_tracks(songs)

    return request.formatter(
        "searchResult3",
        OrderedDict(
            (
                ("artist", [a.as_subsonic_artist(ctx) for a in artists]),
                ("album", [a.as_subsonic_album(ctx) for a in albums]),
                (
                    "song",
                    [t.as_subsonic_child(ctx) for t in songs],
                ),
            )
        ),
    )

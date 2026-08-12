# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from datetime import datetime

from flask import request

from ..db import Album, Artist, Folder, SerializationContext, Track
from . import (
    MAX_TIMESTAMP_MS,
    api_routing,
    get_int,
    get_music_folder,
    get_paging,
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


def _paged(query, count, offset, *order_by):
    """Order, page and materialize one of the search result sets."""
    return list(query.order_by(*order_by).limit(count).offset(offset))


def _search_result(tag, artist, album, song):
    """Format a search2/search3 response from its serialized result sets."""
    return request.formatter(tag, {"artist": artist, "album": album, "song": song})


@api_routing("/search")
def old_search():
    artist, album, title, anyf = map(
        request.values.get, ("artist", "album", "title", "any")
    )

    count, offset = get_paging("count")
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

    artist_count, artist_offset = get_paging("artistCount", "artistOffset")
    album_count, album_offset = get_paging("albumCount", "albumOffset")
    song_count, song_offset = get_paging("songCount", "songOffset")
    root = get_music_folder()

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

    artists = _paged(artists, artist_count, artist_offset, Folder.name, Folder.id)
    albums = _paged(albums, album_count, album_offset, Folder.name, Folder.id)
    songs = _paged(songs, song_count, song_offset, Track.title, Track.id)

    ctx = SerializationContext(request.user, request.client)
    ctx.add_folders(artists + albums)
    ctx.add_tracks(songs)

    return _search_result(
        "searchResult2",
        [a.as_subsonic_artist(ctx) for a in artists],
        [f.as_subsonic_child(ctx) for f in albums],
        [t.as_subsonic_child(ctx) for t in songs],
    )


@api_routing("/search3")
def search_id3():
    query = request.values["query"]

    artist_count, artist_offset = get_paging("artistCount", "artistOffset")
    album_count, album_offset = get_paging("albumCount", "albumOffset")
    song_count, song_offset = get_paging("songCount", "songOffset")
    root = get_music_folder()

    artists = Artist.select().where(Artist.name.contains(query))
    albums = Album.select().where(Album.name.contains(query))
    songs = Track.select().where(Track.title.contains(query))

    if root is not None:
        # distinct: the join is one row per track, without it an artist or album
        # would be repeated once per matching track
        artists = artists.join(Track).where(Track.root_folder == root).distinct()
        albums = albums.join(Track).where(Track.root_folder == root).distinct()
        songs = songs.where(Track.root_folder == root)

    artists = _paged(artists, artist_count, artist_offset, Artist.name, Artist.id)
    albums = _paged(albums, album_count, album_offset, Album.name, Album.id)
    songs = _paged(songs, song_count, song_offset, Track.title, Track.id)

    ctx = SerializationContext(request.user, request.client)
    ctx.add_artists(artists)
    ctx.add_albums(albums)
    ctx.add_tracks(songs)

    return _search_result(
        "searchResult3",
        [a.as_subsonic_artist(ctx) for a in artists],
        [a.as_subsonic_album(ctx) for a in albums],
        [t.as_subsonic_child(ctx) for t in songs],
    )

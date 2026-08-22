# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from ..db import Playlist, PlaylistTrack, SerializationContext, Track, User, db
from ..parsers import parse_int
from ._blueprint import api_routing
from ._exceptions import Forbidden, InvalidParameter, MissingParameter
from ._helpers import get_bool, get_entity, get_entity_id


def _parse_song_index(value):
    """songIndexToRemove is a repeated parameter, so it can't go through get_int.

    Left unbounded on purpose: Playlist.remove_at_indexes already ignores negative
    and out-of-range indexes.
    """
    try:
        index = parse_int(value)
    except ValueError as e:
        raise InvalidParameter("songIndexToRemove", e) from e

    if index is None:
        raise InvalidParameter("songIndexToRemove", "not an integer")
    return index


@api_routing("/getPlaylists")
def list_playlists():
    query = (
        Playlist.select()
        .orwhere(Playlist.user == request.user, Playlist.public)
        .order_by(Playlist.name)
    )

    username = request.values.get("username")
    if username:
        if not request.user.admin:
            raise Forbidden()

        # get rather than join in the following query to raise an exception if the
        # requested user doesn't exist
        user = User.get(name=username)
        query = Playlist.select().where(Playlist.user == user).order_by(Playlist.name)

    return request.formatter(
        "playlists",
        {"playlist": [p.as_subsonic_playlist(request.user) for p in query]},
    )


@api_routing("/getPlaylist")
def show_playlist():
    res = get_entity(Playlist)
    if res.user != request.user and not res.public and not request.user.admin:
        raise Forbidden()

    tracks = res.get_tracks()
    ctx = SerializationContext(request.user, request.client)
    ctx.add_tracks(tracks)

    info = res.as_subsonic_playlist(request.user)
    info["entry"] = [t.as_subsonic_child(ctx) for t in tracks]
    return request.formatter("playlist", info)


@api_routing("/createPlaylist")
@db.atomic()
def create_playlist():
    playlist_id, name = map(request.values.get, ("playlistId", "name"))
    # songId actually doesn't seem to be required
    songs = request.values.getlist("songId")
    playlist_id = get_entity_id(Playlist, playlist_id) if playlist_id else None

    if playlist_id:
        playlist = Playlist[playlist_id]

        if playlist.user != request.user and not request.user.admin:
            raise Forbidden()

        playlist.clear()
        if name:
            playlist.name = name
    elif name:
        playlist = Playlist.create(user=request.user, name=name)
    else:
        raise MissingParameter("playlistId or name")

    for sid in songs:
        sid = get_entity_id(Track, sid)
        track = Track[sid]
        playlist.add(track)
    playlist.save()

    return request.formatter.empty


@api_routing("/deletePlaylist")
def delete_playlist():
    res = get_entity(Playlist)
    if res.user != request.user and not request.user.admin:
        raise Forbidden()

    PlaylistTrack.delete().where(PlaylistTrack.playlist == res).execute()
    res.delete_instance()
    return request.formatter.empty


@api_routing("/updatePlaylist")
def update_playlist():
    res = get_entity(Playlist, "playlistId")
    if res.user != request.user and not request.user.admin:
        raise Forbidden()

    playlist = res
    name, comment = map(request.values.get, ("name", "comment"))
    public = get_bool("public")
    to_add, to_remove = map(
        request.values.getlist, ("songIdToAdd", "songIndexToRemove")
    )

    if name:
        playlist.name = name
    if comment:
        playlist.comment = comment
    if public is not None:
        playlist.public = public

    to_add = [get_entity_id(Track, i) for i in to_add]
    to_remove = [_parse_song_index(i) for i in to_remove]

    for sid in to_add:
        track = Track[sid]
        playlist.add(track)

    playlist.remove_at_indexes(to_remove)
    playlist.save()

    return request.formatter.empty

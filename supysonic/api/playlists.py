# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from flask import request

from ..db import Playlist, User, Track

from . import api, get_entity
from .exceptions import Forbidden, MissingParameter, NotFound


@api.route("/getPlaylists.view", methods=["GET", "POST"])
def list_playlists():
    query = Playlist.select(
        lambda p: p.user.id == request.user.id or p.public
    ).order_by(Playlist.name)

    username = request.values.get("username")
    if username:
        if not request.user.admin:
            raise Forbidden()

        user = User.get(name=username)
        if user is None:
            raise NotFound("User")

        query = Playlist.select(lambda p: p.user.name == username).order_by(
            Playlist.name
        )

    return request.formatter(
        "playlists",
        dict(playlist=[p.as_subsonic_playlist(request.user) for p in query]),
    )


@api.route("/getPlaylist.view", methods=["GET", "POST"])
def show_playlist():
    res = get_entity(Playlist)
    if res.user.id != request.user.id and not res.public and not request.user.admin:
        raise Forbidden()

    info = res.as_subsonic_playlist(request.user)
    info["entry"] = [
        t.as_subsonic_child(request.user, request.client) for t in res.get_tracks()
    ]
    return request.formatter("playlist", info)


@api.route("/createPlaylist.view", methods=["GET", "POST"])
def create_playlist():
    playlist_id, name = map(request.values.get, ["playlistId", "name"])
    # songId actually doesn't seem to be required
    songs = request.values.getlist("songId")
    playlist_id = uuid.UUID(playlist_id) if playlist_id else None

    if playlist_id:
        playlist = Playlist[playlist_id]

        if playlist.user.id != request.user.id and not request.user.admin:
            raise Forbidden()

        playlist.clear()
        if name:
            playlist.name = name
    elif name:
        playlist = Playlist(user=request.user, name=name)
    else:
        raise MissingParameter("playlistId or name")

    for sid in songs:
        sid = uuid.UUID(sid)
        track = Track[sid]
        playlist.add(track)

    return request.formatter.empty


@api.route("/deletePlaylist.view", methods=["GET", "POST"])
def delete_playlist():
    res = get_entity(Playlist)
    if res.user.id != request.user.id and not request.user.admin:
        raise Forbidden()

    res.delete()
    return request.formatter.empty


@api.route("/updatePlaylist.view", methods=["GET", "POST"])
def update_playlist():
    res = get_entity(Playlist, "playlistId")
    if res.user.id != request.user.id and not request.user.admin:
        raise Forbidden()

    playlist = res
    name, comment, public = map(request.values.get, ["name", "comment", "public"])
    to_add, to_remove = map(
        request.values.getlist, ["songIdToAdd", "songIndexToRemove"]
    )

    if name:
        playlist.name = name
    if comment:
        playlist.comment = comment
    if public:
        playlist.public = public in (True, "True", "true", 1, "1")

    to_add = map(uuid.UUID, to_add)
    to_remove = map(int, to_remove)

    for sid in to_add:
        track = Track[sid]
        playlist.add(track)

    playlist.remove_at_indexes(to_remove)

    return request.formatter.empty

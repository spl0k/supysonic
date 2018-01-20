# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2018  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import uuid

from flask import request, current_app as app
from pony.orm import db_session, rollback
from pony.orm import ObjectNotFound

from ..db import Playlist, User, Track
from ..py23 import dict

from . import get_entity

@app.route('/rest/getPlaylists.view', methods = [ 'GET', 'POST' ])
def list_playlists():
    query = Playlist.select(lambda p: p.user.id == request.user.id or p.public).order_by(Playlist.name)

    username = request.values.get('username')
    if username:
        if not request.user.admin:
            return request.error_formatter(50, 'Restricted to admins')

        with db_session:
            user = User.get(name = username)
        if user is None:
            return request.error_formatter(70, 'No such user')

        query = Playlist.select(lambda p: p.user.name == username).order_by(Playlist.name)

    with db_session:
        return request.formatter(dict(playlists = dict(playlist = [ p.as_subsonic_playlist(request.user) for p in query ] )))

@app.route('/rest/getPlaylist.view', methods = [ 'GET', 'POST' ])
@db_session
def show_playlist():
    status, res = get_entity(request, Playlist)
    if not status:
        return res

    if res.user.id != request.user.id and not request.user.admin:
        return request.error_formatter('50', 'Private playlist')

    info = res.as_subsonic_playlist(request.user)
    info['entry'] = [ t.as_subsonic_child(request.user, request.client) for t in res.get_tracks() ]
    return request.formatter(dict(playlist = info))

@app.route('/rest/createPlaylist.view', methods = [ 'GET', 'POST' ])
@db_session
def create_playlist():
    playlist_id, name = map(request.values.get, [ 'playlistId', 'name' ])
    # songId actually doesn't seem to be required
    songs = request.values.getlist('songId')
    try:
        playlist_id = uuid.UUID(playlist_id) if playlist_id else None
    except ValueError:
        return request.error_formatter(0, 'Invalid playlist id')

    if playlist_id:
        try:
            playlist = Playlist[playlist_id]
        except ObjectNotFound:
            return request.error_formatter(70, 'Unknwon playlist')

        if playlist.user.id != request.user.id and not request.user.admin:
            return request.error_formatter(50, "You're not allowed to modify a playlist that isn't yours")

        playlist.clear()
        if name:
            playlist.name = name
    elif name:
        playlist = Playlist(user = User[request.user.id], name = name)
    else:
        return request.error_formatter(10, 'Missing playlist id or name')

    try:
        songs = map(uuid.UUID, songs)
        for sid in songs:
            track = Track[sid]
            playlist.add(track)
    except ValueError:
        rollback()
        return request.error_formatter(0, 'Invalid song id')
    except ObjectNotFound:
        rollback()
        return request.error_formatter(70, 'Unknown song')

    return request.formatter(dict())

@app.route('/rest/deletePlaylist.view', methods = [ 'GET', 'POST' ])
@db_session
def delete_playlist():
    status, res = get_entity(request, Playlist)
    if not status:
        return res

    if res.user.id != request.user.id and not request.user.admin:
        return request.error_formatter(50, "You're not allowed to delete a playlist that isn't yours")

    res.delete()
    return request.formatter(dict())

@app.route('/rest/updatePlaylist.view', methods = [ 'GET', 'POST' ])
@db_session
def update_playlist():
    status, res = get_entity(request, Playlist, 'playlistId')
    if not status:
        return res

    if res.user.id != request.user.id and not request.user.admin:
        return request.error_formatter(50, "You're not allowed to delete a playlist that isn't yours")

    playlist = res
    name, comment, public = map(request.values.get, [ 'name', 'comment', 'public' ])
    to_add, to_remove = map(request.values.getlist, [ 'songIdToAdd', 'songIndexToRemove' ])

    if name:
        playlist.name = name
    if comment:
        playlist.comment = comment
    if public:
        playlist.public = public in (True, 'True', 'true', 1, '1')

    try:
        to_add = map(uuid.UUID, to_add)
        to_remove = map(int, to_remove)

        for sid in to_add:
            track = Track[sid]
            playlist.add(track)

        playlist.remove_at_indexes(to_remove)
    except ValueError:
        return request.error_formatter(0, 'Invalid parameter')
    except ObjectNotFound:
        return request.error_formatter(70, 'Unknown song')

    return request.formatter(dict())


# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2017  Alban 'spl0k' Féron
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

from ..db import Playlist, User, Track

from . import get_entity

@app.route('/rest/getPlaylists.view', methods = [ 'GET', 'POST' ])
def list_playlists():
    query = store.find(Playlist, Or(Playlist.user_id == request.user.id, Playlist.public == True)).order_by(Playlist.name)

    username = request.values.get('username')
    if username:
        if not request.user.admin:
            return request.error_formatter(50, 'Restricted to admins')

        user = store.find(User, User.name == username).one()
        if not user:
            return request.error_formatter(70, 'No such user')

        query = store.find(Playlist, Playlist.user_id == User.id, User.name == username).order_by(Playlist.name)

    return request.formatter({ 'playlists': { 'playlist': [ p.as_subsonic_playlist(request.user) for p in query ] } })

@app.route('/rest/getPlaylist.view', methods = [ 'GET', 'POST' ])
def show_playlist():
    status, res = get_entity(request, Playlist)
    if not status:
        return res

    if res.user_id != request.user.id and not request.user.admin:
        return request.error_formatter('50', 'Private playlist')

    info = res.as_subsonic_playlist(request.user)
    info['entry'] = [ t.as_subsonic_child(request.user, request.prefs) for t in res.get_tracks() ]
    return request.formatter({ 'playlist': info })

@app.route('/rest/createPlaylist.view', methods = [ 'GET', 'POST' ])
def create_playlist():
    # Only(?) method where the android client uses form data rather than GET params
    playlist_id, name = map(request.values.get, [ 'playlistId', 'name' ])
    # songId actually doesn't seem to be required
    songs = request.values.getlist('songId')
    try:
        playlist_id = uuid.UUID(playlist_id) if playlist_id else None
        songs = map(uuid.UUID, songs)
    except:
        return request.error_formatter(0, 'Invalid parameter')

    if playlist_id:
        playlist = store.get(Playlist, playlist_id)
        if not playlist:
            return request.error_formatter(70, 'Unknwon playlist')

        if playlist.user_id != request.user.id and not request.user.admin:
            return request.error_formatter(50, "You're not allowed to modify a playlist that isn't yours")

        playlist.clear()
        if name:
            playlist.name = name
    elif name:
        playlist = Playlist()
        playlist.user_id = request.user.id
        playlist.name = name
        store.add(playlist)
    else:
        return request.error_formatter(10, 'Missing playlist id or name')

    for sid in songs:
        track = store.get(Track, sid)
        if not track:
            store.rollback()
            return request.error_formatter(70, 'Unknown song')

        playlist.add(track)

    store.commit()
    return request.formatter({})

@app.route('/rest/deletePlaylist.view', methods = [ 'GET', 'POST' ])
def delete_playlist():
    status, res = get_entity(request, Playlist)
    if not status:
        return res

    if res.user_id != request.user.id and not request.user.admin:
        return request.error_formatter(50, "You're not allowed to delete a playlist that isn't yours")

    store.remove(res)
    store.commit()
    return request.formatter({})

@app.route('/rest/updatePlaylist.view', methods = [ 'GET', 'POST' ])
def update_playlist():
    status, res = get_entity(request, Playlist, 'playlistId')
    if not status:
        return res

    if res.user_id != request.user.id and not request.user.admin:
        return request.error_formatter(50, "You're not allowed to delete a playlist that isn't yours")

    playlist = res
    name, comment, public = map(request.values.get, [ 'name', 'comment', 'public' ])
    to_add, to_remove = map(request.values.getlist, [ 'songIdToAdd', 'songIndexToRemove' ])
    try:
        to_add = map(uuid.UUID, to_add)
        to_remove = map(int, to_remove)
    except:
        return request.error_formatter(0, 'Invalid parameter')

    if name:
        playlist.name = name
    if comment:
        playlist.comment = comment
    if public:
        playlist.public = public in (True, 'True', 'true', 1, '1')

    for sid in to_add:
        track = store.get(Track, sid)
        if not track:
            return request.error_formatter(70, 'Unknown song')
        playlist.add(track)

    playlist.remove_at_indexes(to_remove)

    store.commit()
    return request.formatter({})


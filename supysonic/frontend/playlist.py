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

from flask import request, flash, render_template, redirect, url_for, current_app as app
from pony.orm import db_session
from pony.orm import ObjectNotFound

from ..db import Playlist
from ..managers.user import UserManager

@app.route('/playlist')
@db_session
def playlist_index():
    return render_template('playlists.html',
        mine = Playlist.select(lambda p: p.user == request.user),
        others = Playlist.select(lambda p: p.user != request.user and p.public))

@app.route('/playlist/<uid>')
@db_session
def playlist_details(uid):
    try:
        uid = uuid.UUID(uid)
    except ValueError:
        flash('Invalid playlist id')
        return redirect(url_for('playlist_index'))

    try:
        playlist = Playlist[uid]
    except ObjectNotFound:
        flash('Unknown playlist')
        return redirect(url_for('playlist_index'))

    return render_template('playlist.html', playlist = playlist)

@app.route('/playlist/<uid>', methods = [ 'POST' ])
@db_session
def playlist_update(uid):
    try:
        uid = uuid.UUID(uid)
    except ValueError:
        flash('Invalid playlist id')
        return redirect(url_for('playlist_index'))

    try:
        playlist = Playlist[uid]
    except ObjectNotFound:
        flash('Unknown playlist')
        return redirect(url_for('playlist_index'))

    if playlist.user.id != request.user.id:
        flash("You're not allowed to edit this playlist")
    elif not request.form.get('name'):
        flash('Missing playlist name')
    else:
        playlist.name = request.form.get('name')
        playlist.public = request.form.get('public') in (True, 'True', 1, '1', 'on', 'checked')
        flash('Playlist updated.')

    return playlist_details(str(uid))

@app.route('/playlist/del/<uid>')
@db_session
def playlist_delete(uid):
    try:
        uid = uuid.UUID(uid)
    except ValueError:
        flash('Invalid playlist id')
        return redirect(url_for('playlist_index'))

    try:
        playlist = Playlist[uid]
    except ObjectNotFound:
        flash('Unknown playlist')
        return redirect(url_for('playlist_index'))

    if playlist.user.id != request.user.id:
        flash("You're not allowed to delete this playlist")
    else:
        playlist.delete()
        flash('Playlist deleted')

    return redirect(url_for('playlist_index'))


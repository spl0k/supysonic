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

import random
import uuid

from datetime import timedelta
from flask import request, current_app as app
from pony.orm import db_session, select, desc, avg, max, min, count

from ..db import Folder, Artist, Album, Track, RatingFolder, StarredFolder, StarredArtist, StarredAlbum, StarredTrack, User
from ..db import now

from builtins import dict

@app.route('/rest/getRandomSongs.view', methods = [ 'GET', 'POST' ])
def rand_songs():
    size = request.values.get('size', '10')
    genre, fromYear, toYear, musicFolderId = map(request.values.get, [ 'genre', 'fromYear', 'toYear', 'musicFolderId' ])

    try:
        size = int(size) if size else 10
        fromYear = int(fromYear) if fromYear else None
        toYear = int(toYear) if toYear else None
        fid = uuid.UUID(musicFolderId) if musicFolderId else None
    except:
        return request.error_formatter(0, 'Invalid parameter format')

    query = Track.select()
    if fromYear:
        query = query.filter(lambda t: t.year >= fromYear)
    if toYear:
        query = query.filter(lambda t: t.year <= toYear)
    if genre:
        query = query.filter(lambda t: t.genre == genre)
    if fid:
        with db_session:
            if not Folder.exists(id = fid, root = True):
                return request.error_formatter(70, 'Unknown folder')

        query = query.filter(lambda t: t.root_folder.id == fid)

    with db_session:
        return request.formatter(dict(
            randomSongs = dict(
                song = [ t.as_subsonic_child(request.user, request.client) for t in query.random(size) ]
            )
        ))

@app.route('/rest/getAlbumList.view', methods = [ 'GET', 'POST' ])
def album_list():
    ltype, size, offset = map(request.values.get, [ 'type', 'size', 'offset' ])
    if not ltype:
        return request.error_formatter(10, 'Missing type')
    try:
        size = int(size) if size else 10
        offset = int(offset) if offset else 0
    except:
        return request.error_formatter(0, 'Invalid parameter format')

    query = select(t.folder for t in Track)
    if ltype == 'random':
        with db_session:
            return request.formatter(dict(
                albumList = dict(
                    album = [ a.as_subsonic_child(request.user) for a in query.random(size) ]
                )
            ))
    elif ltype == 'newest':
        query = query.order_by(desc(Folder.created))
    elif ltype == 'highest':
        query = query.order_by(lambda f: desc(avg(f.ratings.rating)))
    elif ltype == 'frequent':
        query = query.order_by(lambda f: desc(avg(f.tracks.play_count)))
    elif ltype == 'recent':
        query = query.order_by(lambda f: desc(max(f.tracks.last_play)))
    elif ltype == 'starred':
        query = select(s.starred for s in StarredFolder if s.user.id == request.user.id and count(s.starred.tracks) > 0)
    elif ltype == 'alphabeticalByName':
        query = query.order_by(Folder.name)
    elif ltype == 'alphabeticalByArtist':
        query = query.order_by(lambda f: f.parent.name + f.name)
    else:
        return request.error_formatter(0, 'Unknown search type')

    with db_session:
        return request.formatter(dict(
            albumList = dict(
                album = [ f.as_subsonic_child(request.user) for f in query.limit(size, offset) ]
            )
        ))

@app.route('/rest/getAlbumList2.view', methods = [ 'GET', 'POST' ])
def album_list_id3():
    ltype, size, offset = map(request.values.get, [ 'type', 'size', 'offset' ])
    if not ltype:
        return request.error_formatter(10, 'Missing type')
    try:
        size = int(size) if size else 10
        offset = int(offset) if offset else 0
    except:
        return request.error_formatter(0, 'Invalid parameter format')

    query = Album.select()
    if ltype == 'random':
        with db_session:
            return request.formatter(dict(
                albumList2 = dict(
                    album = [ a.as_subsonic_album(request.user) for a in query.random(size) ]
                )
            ))
    elif ltype == 'newest':
        query = query.order_by(lambda a: desc(min(a.tracks.created)))
    elif ltype == 'frequent':
        query = query.order_by(lambda a: desc(avg(a.tracks.play_count)))
    elif ltype == 'recent':
        query = query.order_by(lambda a: desc(max(a.tracks.last_play)))
    elif ltype == 'starred':
        query = select(s.starred for s in StarredAlbum if s.user.id == request.user.id)
    elif ltype == 'alphabeticalByName':
        query = query.order_by(Album.name)
    elif ltype == 'alphabeticalByArtist':
        query = query.order_by(lambda a: a.artist.name + a.name)
    else:
        return request.error_formatter(0, 'Unknown search type')

    with db_session:
        return request.formatter(dict(
            albumList2 = dict(
                album = [ f.as_subsonic_album(request.user) for f in query.limit(size, offset) ]
            )
        ))

@app.route('/rest/getNowPlaying.view', methods = [ 'GET', 'POST' ])
@db_session
def now_playing():
    query = User.select(lambda u: u.last_play is not None and u.last_play_date + timedelta(minutes = 3) > now())

    return request.formatter(dict(
        nowPlaying = dict(
            entry = [ dict(
                u.last_play.as_subsonic_child(request.user, request.client),
                username = u.name, minutesAgo = (now() - u.last_play_date).seconds / 60, playerId = 0
            ) for u in query ]
        )
    ))

@app.route('/rest/getStarred.view', methods = [ 'GET', 'POST' ])
@db_session
def get_starred():
    folders = select(s.starred for s in StarredFolder if s.user.id == request.user.id)

    return request.formatter(dict(
        starred = dict(
            artist = [ dict(id = str(sf.id), name = sf.name) for sf in folders.filter(lambda f: count(f.tracks) == 0) ],
            album = [ sf.as_subsonic_child(request.user) for sf in folders.filter(lambda f: count(f.tracks) > 0) ],
            song = [ st.as_subsonic_child(request.user, request.client) for st in select(s.starred for s in StarredTrack if s.user.id == request.user.id) ]
        )
    ))

@app.route('/rest/getStarred2.view', methods = [ 'GET', 'POST' ])
@db_session
def get_starred_id3():
    return request.formatter(dict(
        starred2 = dict(
            artist = [ sa.as_subsonic_artist(request.user) for sa in select(s.starred for s in StarredArtist if s.user.id == request.user.id) ],
            album = [ sa.as_subsonic_album(request.user) for sa in select(s.starred for s in StarredAlbum if s.user.id == request.user.id) ],
            song = [ st.as_subsonic_child(request.user, request.client) for st in select(s.starred for s in StarredTrack if s.user.id == request.user.id) ]
        )
    ))


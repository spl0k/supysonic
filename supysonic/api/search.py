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

from datetime import datetime
from flask import request, current_app as app
from pony.orm import db_session, select

from ..db import Folder, Track, Artist, Album

@app.route('/rest/search.view', methods = [ 'GET', 'POST' ])
def old_search():
    artist, album, title, anyf, count, offset, newer_than = map(request.values.get, [ 'artist', 'album', 'title', 'any', 'count', 'offset', 'newerThan' ])
    try:
        count = int(count) if count else 20
        offset = int(offset) if offset else 0
        newer_than = int(newer_than) / 1000 if newer_than else 0
    except:
        return request.error_formatter(0, 'Invalid parameter')

    min_date = datetime.fromtimestamp(newer_than)

    if artist:
        query = select(t.folder.parent for t in Track if artist in t.folder.parent.name and t.folder.parent.created > min_date)
    elif album:
        query = select(t.folder for t in Track if album in t.folder.name and t.folder.created > min_date)
    elif title:
        query = Track.select(lambda t: title in t.title and t.created > min_date)
    elif anyf:
        folders = Folder.select(lambda f: anyf in f.name and f.created > min_date)
        tracks = Track.select(lambda t: anyf in t.title and t.created > min_date)
        with db_session:
            res = folders[offset : offset + count]
            fcount = folders.count()
            if offset + count > fcount:
                toff = max(0, offset - fcount)
                tend = offset + count - fcount
                res += tracks[toff : tend]

            return request.formatter({ 'searchResult': {
                'totalHits': folders.count() + tracks.count(),
                'offset': offset,
                'match': [ r.as_subsonic_child(request.user) if isinstance(r, Folder) else r.as_subsonic_child(request.user, request.prefs) for r in res ]
            }})
    else:
        return request.error_formatter(10, 'Missing search parameter')

    with db_session:
        return request.formatter({ 'searchResult': {
            'totalHits': query.count(),
            'offset': offset,
            'match': [ r.as_subsonic_child(request.user) if isinstance(r, Folder) else r.as_subsonic_child(request.user, request.prefs) for r in query[offset : offset + count] ]
        }})

@app.route('/rest/search2.view', methods = [ 'GET', 'POST' ])
def new_search():
    query, artist_count, artist_offset, album_count, album_offset, song_count, song_offset = map(
        request.values.get, [ 'query', 'artistCount', 'artistOffset', 'albumCount', 'albumOffset', 'songCount', 'songOffset' ])

    try:
        artist_count =  int(artist_count)  if artist_count  else 20
        artist_offset = int(artist_offset) if artist_offset else 0
        album_count =   int(album_count)   if album_count   else 20
        album_offset =  int(album_offset)  if album_offset  else 0
        song_count =    int(song_count)    if song_count    else 20
        song_offset =   int(song_offset)   if song_offset   else 0
    except:
        return request.error_formatter(0, 'Invalid parameter')

    if not query:
        return request.error_formatter(10, 'Missing query parameter')

    with db_session:
        artists = select(t.folder.parent for t in Track if query in t.folder.parent.name).limit(artist_count, artist_offset)
        albums = select(t.folder for t in Track if query in t.folder.name).limit(album_count, album_offset)
        songs = Track.select(lambda t: query in t.title).limit(song_count, song_offset)

        return request.formatter({ 'searchResult2': {
            'artist': [ { 'id': str(a.id), 'name': a.name } for a in artists ],
            'album': [ f.as_subsonic_child(request.user) for f in albums ],
            'song': [ t.as_subsonic_child(request.user, request.prefs) for t in songs ]
        }})

@app.route('/rest/search3.view', methods = [ 'GET', 'POST' ])
def search_id3():
    query, artist_count, artist_offset, album_count, album_offset, song_count, song_offset = map(
        request.values.get, [ 'query', 'artistCount', 'artistOffset', 'albumCount', 'albumOffset', 'songCount', 'songOffset' ])

    try:
        artist_count =  int(artist_count)  if artist_count  else 20
        artist_offset = int(artist_offset) if artist_offset else 0
        album_count =   int(album_count)   if album_count   else 20
        album_offset =  int(album_offset)  if album_offset  else 0
        song_count =    int(song_count)    if song_count    else 20
        song_offset =   int(song_offset)   if song_offset   else 0
    except:
        return request.error_formatter(0, 'Invalid parameter')

    if not query:
        return request.error_formatter(10, 'Missing query parameter')

    with db_session:
        artists = Artist.select(lambda a: query in a.name).limit(artist_count, artist_offset)
        albums = Album.select(lambda a: query in a.name).limit(album_count, album_offset)
        songs = Track.select(lambda t: query in t.title).limit(song_count, song_offset)

        return request.formatter({ 'searchResult3': {
            'artist': [ a.as_subsonic_artist(request.user) for a in artists ],
            'album': [ a.as_subsonic_album(request.user) for a in albums ],
            'song': [ t.as_subsonic_child(request.user, request.prefs) for t in songs ]
        }})


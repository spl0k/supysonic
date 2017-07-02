# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013  Alban 'spl0k' Féron
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

from flask import request
from storm.info import ClassAlias
from supysonic.web import app, store
from supysonic.db import Folder, Track, Artist, Album

@app.route('/rest/search.view', methods = [ 'GET', 'POST' ])
def old_search():
	artist, album, title, anyf, count, offset, newer_than = map(request.values.get, [ 'artist', 'album', 'title', 'any', 'count', 'offset', 'newerThan' ])
	try:
		count = int(count) if count else 20
		offset = int(offset) if offset else 0
		newer_than = int(newer_than) if newer_than else 0
	except:
		return request.error_formatter(0, 'Invalid parameter')

	if artist:
		parent = ClassAlias(Folder)
		query = store.find(parent, Folder.parent_id == parent.id, Track.folder_id == Folder.id, parent.name.contains_string(artist)).config(distinct = True)
	elif album:
		query = store.find(Folder, Track.folder_id == Folder.id, Folder.name.contains_string(album)).config(distinct = True)
	elif title:
		query = store.find(Track, Track.title.contains_string(title))
	elif anyf:
		folders = store.find(Folder, Folder.name.contains_string(anyf))
		tracks = store.find(Track, Track.title.contains_string(anyf))
		res = list(folders[offset : offset + count])
		if offset + count > folders.count():
			toff = max(0, offset - folders.count())
			tend = offset + count - folders.count()
			res += list(tracks[toff : tend])

		return request.formatter({ 'searchResult': {
			'totalHits': folders.count() + tracks.count(),
			'offset': offset,
			'match': [ r.as_subsonic_child(request.user) if r is Folder else r.as_subsonic_child(request.user, request.prefs) for r in res ]
		}})
	else:
		return request.error_formatter(10, 'Missing search parameter')

	return request.formatter({ 'searchResult': {
		'totalHits': query.count(),
		'offset': offset,
		'match': [ r.as_subsonic_child(request.user) if r is Folder else r.as_subsonic_child(request.user, request.prefs) for r in query[offset : offset + count] ]
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

	parent = ClassAlias(Folder)
	artist_query = store.find(parent, Folder.parent_id == parent.id, Track.folder_id == Folder.id, parent.name.contains_string(query)).config(distinct = True, offset = artist_offset, limit = artist_count)
	album_query = store.find(Folder, Track.folder_id == Folder.id, Folder.name.contains_string(query)).config(distinct = True, offset = album_offset, limit = album_count)
	song_query = store.find(Track, Track.title.contains_string(query))[song_offset : song_offset + song_count]

	return request.formatter({ 'searchResult2': {
		'artist': [ { 'id': str(a.id), 'name': a.name } for a in artist_query ],
		'album': [ f.as_subsonic_child(request.user) for f in album_query ],
		'song': [ t.as_subsonic_child(request.user, request.prefs) for t in song_query ]
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

	artist_query = store.find(Artist, Artist.name.contains_string(query))[artist_offset : artist_offset + artist_count]
	album_query = store.find(Album, Album.name.contains_string(query))[album_offset : album_offset + album_count]
	song_query = store.find(Track, Track.title.contains_string(query))[song_offset : song_offset + song_count]

	return request.formatter({ 'searchResult3': {
		'artist': [ a.as_subsonic_artist(request.user) for a in artist_query ],
		'album': [ a.as_subsonic_album(request.user) for a in album_query ],
		'song': [ t.as_subsonic_child(request.user, request.prefs) for t in song_query ]
	}})


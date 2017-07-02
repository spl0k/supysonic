# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013, 2014  Alban 'spl0k' Féron
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
from storm.expr import Desc, Avg, Min, Max
from storm.info import ClassAlias
from datetime import timedelta
import random
import uuid

from supysonic.web import app, store
from supysonic.db import Folder, Artist, Album, Track, RatingFolder, StarredFolder, StarredArtist, StarredAlbum, StarredTrack, User
from supysonic.db import now

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

	query = store.find(Track)
	if fromYear:
		query = query.find(Track.year >= fromYear)
	if toYear:
		query = query.find(Track.year <= toYear)
	if genre:
		query = query.find(Track.genre == genre)
	if fid:
		query = query.find(Track.root_folder_id == fid)
	count = query.count()

	if not count:
		return request.formatter({ 'randomSongs': {} })

	tracks = []
	for _ in xrange(size):
		x = random.choice(xrange(count))
		tracks.append(query[x])

	return request.formatter({
		'randomSongs': {
			'song': [ t.as_subsonic_child(request.user, request.prefs) for t in tracks ]
		}
	})

@app.route('/rest/getAlbumList.view', methods = [ 'GET', 'POST' ])
def album_list():
	ltype, size, offset = map(request.values.get, [ 'type', 'size', 'offset' ])
	try:
		size = int(size) if size else 10
		offset = int(offset) if offset else 0
	except:
		return request.error_formatter(0, 'Invalid parameter format')

	query = store.find(Folder, Track.folder_id == Folder.id)
	if ltype == 'random':
		albums = []
		count = query.count()

		if not count:
			return request.formatter({ 'albumList': {} })

		for _ in xrange(size):
			x = random.choice(xrange(count))
			albums.append(query[x])

		return request.formatter({
			'albumList': {
				'album': [ a.as_subsonic_child(request.user) for a in albums ]
			}
		})
	elif ltype == 'newest':
		query = query.order_by(Desc(Folder.created)).config(distinct = True)
	elif ltype == 'highest':
		query = query.find(RatingFolder.rated_id == Folder.id).group_by(Folder.id).order_by(Desc(Avg(RatingFolder.rating)))
	elif ltype == 'frequent':
		query = query.group_by(Folder.id).order_by(Desc(Avg(Track.play_count)))
	elif ltype == 'recent':
		query = query.group_by(Folder.id).order_by(Desc(Max(Track.last_play)))
	elif ltype == 'starred':
		query = query.find(StarredFolder.starred_id == Folder.id, User.id == StarredFolder.user_id, User.name == request.username)
	elif ltype == 'alphabeticalByName':
		query = query.order_by(Folder.name).config(distinct = True)
	elif ltype == 'alphabeticalByArtist':
		parent = ClassAlias(Folder)
		query = query.find(Folder.parent_id == parent.id).order_by(parent.name, Folder.name).config(distinct = True)
	else:
		return request.error_formatter(0, 'Unknown search type')

	return request.formatter({
		'albumList': {
			'album': [ f.as_subsonic_child(request.user) for f in query[offset:offset+size] ]
		}
	})

@app.route('/rest/getAlbumList2.view', methods = [ 'GET', 'POST' ])
def album_list_id3():
	ltype, size, offset = map(request.values.get, [ 'type', 'size', 'offset' ])
	try:
		size = int(size) if size else 10
		offset = int(offset) if offset else 0
	except:
		return request.error_formatter(0, 'Invalid parameter format')

	query = store.find(Album)
	if ltype == 'random':
		albums = []
		count = query.count()

		if not count:
			return request.formatter({ 'albumList2': {} })

		for _ in xrange(size):
			x = random.choice(xrange(count))
			albums.append(query[x])

		return request.formatter({
			'albumList2': {
				'album': [ a.as_subsonic_album(request.user) for a in albums ]
			}
		})
	elif ltype == 'newest':
		query = query.find(Track.album_id == Album.id).group_by(Album.id).order_by(Desc(Min(Track.created)))
	elif ltype == 'frequent':
		query = query.find(Track.album_id == Album.id).group_by(Album.id).order_by(Desc(Avg(Track.play_count)))
	elif ltype == 'recent':
		query = query.find(Track.album_id == Album.id).group_by(Album.id).order_by(Desc(Max(Track.last_play)))
	elif ltype == 'starred':
		query = query.find(StarredAlbum.starred_id == Album.id, User.id == StarredAlbum.user_id, User.name == request.username)
	elif ltype == 'alphabeticalByName':
		query = query.order_by(Album.name)
	elif ltype == 'alphabeticalByArtist':
		query = query.find(Artist.id == Album.artist_id).order_by(Artist.name, Album.name)
	else:
		return request.error_formatter(0, 'Unknown search type')

	return request.formatter({
		'albumList2': {
			'album': [ f.as_subsonic_album(request.user) for f in query[offset:offset+size] ]
		}
	})

@app.route('/rest/getNowPlaying.view', methods = [ 'GET', 'POST' ])
def now_playing():
	query = store.find(User, Track.id == User.last_play_id)

	return request.formatter({
		'nowPlaying': {
			'entry': [ dict(
				u.last_play.as_subsonic_child(request.user, request.prefs).items() +
				{ 'username': u.name, 'minutesAgo': (now() - u.last_play_date).seconds / 60, 'playerId': 0 }.items()
			) for u in query if u.last_play_date + timedelta(seconds = u.last_play.duration * 2) > now() ]
		}
	})

@app.route('/rest/getStarred.view', methods = [ 'GET', 'POST' ])
def get_starred():
	folders = store.find(StarredFolder, StarredFolder.user_id == User.id, User.name == request.username)

	return request.formatter({
		'starred': {
			'artist': [ { 'id': str(sf.starred_id), 'name': sf.starred.name } for sf in folders.find(Folder.parent_id == StarredFolder.starred_id, Track.folder_id == Folder.id).config(distinct = True) ],
			'album': [ sf.starred.as_subsonic_child(request.user) for sf in folders.find(Track.folder_id == StarredFolder.starred_id).config(distinct = True) ],
			'song': [ st.starred.as_subsonic_child(request.user, request.prefs) for st in store.find(StarredTrack, StarredTrack.user_id == User.id, User.name == request.username) ]
		}
	})

@app.route('/rest/getStarred2.view', methods = [ 'GET', 'POST' ])
def get_starred_id3():
	return request.formatter({
		'starred2': {
			'artist': [ sa.starred.as_subsonic_artist(request.user) for sa in store.find(StarredArtist, StarredArtist.user_id == User.id, User.name == request.username) ],
			'album': [ sa.starred.as_subsonic_album(request.user) for sa in store.find(StarredAlbum, StarredAlbum.user_id == User.id, User.name == request.username) ],
			'song': [ st.starred.as_subsonic_child(request.user, request.prefs) for st in store.find(StarredTrack, StarredTrack.user_id == User.id, User.name == request.username) ]
		}
	})


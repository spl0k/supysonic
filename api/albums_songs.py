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
from sqlalchemy import desc, func
from sqlalchemy.orm import aliased
import random
import uuid

from web import app
from db import *

@app.route('/rest/getRandomSongs.view', methods = [ 'GET', 'POST' ])
def rand_songs():
	size = request.args.get('size', '10')
	genre, fromYear, toYear, musicFolderId = map(request.args.get, [ 'genre', 'fromYear', 'toYear', 'musicFolderId' ])

	try:
		size = int(size) if size else 10
		fromYear = int(fromYear) if fromYear else None
		toYear = int(toYear) if toYear else None
		fid = uuid.UUID(musicFolderId) if musicFolderId else None
	except:
		return request.error_formatter(0, 'Invalid parameter format')

	query = session.query(Track)
	if fromYear:
		query = query.filter(Track.year >= fromYear)
	if toYear:
		query = query.filter(Track.year <= toYear)
	if genre:
		query = query.filter(Track.genre == genre)
	if fid:
		f = Folder.query.get(fid)
		query = query.filter(Track.path.like(f.path + '%'))
	count = query.count()

	if not count:
		return request.formatter({ 'randomSongs': {} })

	tracks = []
	for _ in xrange(size):
		x = random.choice(xrange(count))
		tracks.append(query.offset(x).limit(1).one())

	return request.formatter({
		'randomSongs': {
			'song': [ t.as_subsonic_child(request.user) for t in tracks ]
		}
	})

@app.route('/rest/getAlbumList.view', methods = [ 'GET', 'POST' ])
def album_list():
	ltype, size, offset = map(request.args.get, [ 'type', 'size', 'offset' ])
	try:
		size = int(size) if size else 10
		offset = int(offset) if offset else 0
	except:
		return request.error_formatter(0, 'Invalid parameter format')

	query = session.query(Folder).filter(Folder.tracks.any())
	if ltype == 'random':
		albums = []
		count = query.count()

		if not count:
			return request.formatter({ 'albumList': {} })

		for _ in xrange(size):
			x = random.choice(xrange(count))
			albums.append(query.offset(x).limit(1).one())

		return request.formatter({
			'albumList': {
				'album': [ a.as_subsonic_child(request.user) for a in albums ]
			}
		})
	elif ltype == 'newest':
		query = query.order_by(desc(Folder.created))
	elif ltype == 'highest':
		query = query.join(RatingFolder).group_by(Folder.id).order_by(desc(func.avg(RatingFolder.rating)))
	elif ltype == 'frequent':
		query = query.join(Track, Folder.tracks).group_by(Folder.id).order_by(desc(func.avg(Track.play_count)))
	elif ltype == 'recent':
		query = query.join(Track, Folder.tracks).group_by(Folder.id).order_by(desc(func.max(Track.last_play)))
	elif ltype == 'starred':
		query = query.join(StarredFolder).join(User).filter(User.name == request.username)
	elif ltype == 'alphabeticalByName':
		query = query.order_by(Folder.name)
	elif ltype == 'alphabeticalByArtist':
		# this is a mess because who knows how your file structure is set up
		# with the database changes it's more difficult to get the parent of a dir
		parent = aliased(Folder)
		query = query.join(parent, Folder.parent).order_by(parent.name).order_by(Folder.name)
	else:
		return request.error_formatter(0, 'Unknown search type')

	return request.formatter({
		'albumList': {
			'album': [ f.as_subsonic_child(request.user) for f in query.limit(size).offset(offset) ]
		}
	})

@app.route('/rest/getAlbumList2.view', methods = [ 'GET', 'POST' ])
def album_list_id3():
	ltype, size, offset = map(request.args.get, [ 'type', 'size', 'offset' ])
	try:
		size = int(size) if size else 10
		offset = int(offset) if offset else 0
	except:
		return request.error_formatter(0, 'Invalid parameter format')

	query = session.query(Album)
	if ltype == 'random':
		albums = []
		count = query.count()

		if not count:
			return request.formatter({ 'albumList2': {} })

		for _ in xrange(size):
			x = random.choice(xrange(count))
			albums.append(query.offset(x).limit(1).one())

		return request.formatter({
			'albumList2': {
				'album': [ a.as_subsonic_album(request.user) for a in albums ]
			}
		})
	elif ltype == 'newest':
		query = query.join(Track, Album.tracks).group_by(Album.id).order_by(desc(func.min(Track.created)))
	elif ltype == 'frequent':
		query = query.join(Track, Album.tracks).group_by(Album.id).order_by(desc(func.avg(Track.play_count)))
	elif ltype == 'recent':
		query = query.join(Track, Album.tracks).group_by(Album.id).order_by(desc(func.max(Track.last_play)))
	elif ltype == 'starred':
		query = query.join(StarredAlbum).join(User).filter(User.name == request.username)
	elif ltype == 'alphabeticalByName':
		query = query.order_by(Album.name)
	elif ltype == 'alphabeticalByArtist':
		query = query.join(Artist).order_by(Artist.name).order_by(Album.name)
	else:
		return request.error_formatter(0, 'Unknown search type')

	return request.formatter({
		'albumList2': {
			'album': [ f.as_subsonic_album(request.user) for f in query.limit(size).offset(offset) ]
		}
	})

@app.route('/rest/getNowPlaying.view', methods = [ 'GET', 'POST' ])
def now_playing():
	if engine.name == 'sqlite':
		query = session.query(User).join(Track).filter(func.strftime('%s', now()) - func.strftime('%s', User.last_play_date) < Track.duration * 2)
	elif engine.name == 'postgresql':
		query = session.query(User).join(Track).filter(func.date_part('epoch', func.now() - User.last_play_date) < Track.duration * 2)
	else:
		query = session.query(User).join(Track).filter(func.timediff(func.now(), User.last_play_date) < Track.duration * 2)

	return request.formatter({
		'nowPlaying': {
			'entry': [ dict(
				u.last_play.as_subsonic_child(request.user).items() +
				{ 'username': u.name, 'minutesAgo': (now() - u.last_play_date).seconds / 60, 'playerId': 0 }.items()
			) for u in query ]
		}
	})

@app.route('/rest/getStarred.view', methods = [ 'GET', 'POST' ])
def get_starred():
	return request.formatter({
		'starred': {
			'artist': [ { 'id': str(sf.starred_id), 'name': sf.starred.name } for sf in session.query(StarredFolder).join(User).join(Folder).filter(User.name == request.username).filter(~ Folder.tracks.any()) ],
			'album': [ sf.starred.as_subsonic_child(request.user) for sf in session.query(StarredFolder).join(User).join(Folder).filter(User.name == request.username).filter(Folder.tracks.any()) ],
			'song': [ st.starred.as_subsonic_child(request.user) for st in session.query(StarredTrack).join(User).filter(User.name == request.username) ]
		}
	})

@app.route('/rest/getStarred2.view', methods = [ 'GET', 'POST' ])
def get_starred_id3():
	return request.formatter({
		'starred2': {
			'artist': [ sa.starred.as_subsonic_artist(request.user) for sa in session.query(StarredArtist).join(User).filter(User.name == request.username) ],
			'album': [ sa.starred.as_subsonic_album(request.user) for sa in session.query(StarredAlbum).join(User).filter(User.name == request.username) ],
			'song': [ st.starred.as_subsonic_child(request.user) for st in session.query(StarredTrack).join(User).filter(User.name == request.username) ]
		}
	})


# coding: utf-8

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

	query = Track.query
	if fromYear:
		query = query.filter(Track.year >= fromYear)
	if toYear:
		query = query.filter(Track.year <= toYear)
	if genre:
		query = query.filter(Track.genre == genre)
	if fid:
		query = query.filter(Track.root_folder_id == fid)
	tracks = query.all()

	if not tracks:
		return request.formatter({ 'randomSongs': {} })

	return request.formatter({
		'randomSongs': {
			'song': [ random.choice(tracks).as_subsonic_child() for x in xrange(size) ]
		}
	})

@app.route('/rest/getAlbumList.view', methods = [ 'GET', 'POST' ])
def album_list():
	username, ltype, size, offset = map(request.args.get, [ 'u', 'type', 'size', 'offset' ])
	try:
		size = int(size) if size else 10
		offset = int(offset) if offset else 0
	except:
		return request.error_formatter(0, 'Invalid parameter format')

	if not username:
		username = request.authorization.username

	query = Folder.query.filter(Folder.tracks.any())
	if ltype == 'random':
		albums = query.all()
		return request.formatter({
			'albumList': {
				'album': [ random.choice(albums).as_subsonic_child() for x in xrange(size) ]
			}
		})
	elif ltype == 'newest':
		query = query.order_by(desc(Folder.created))
	elif ltype == 'highest':
		return request.error_formatter(0, 'Not implemented')
	elif ltype == 'frequent':
		query = query.join(Track, Folder.tracks).group_by(Folder.id).order_by(desc(func.sum(Track.play_count) / func.count()))
	elif ltype == 'recent':
		query = query.join(Track, Folder.tracks).group_by(Folder.id).order_by(desc(func.max(Track.last_play)))
	elif ltype == 'starred':
		query = query.join(StarredFolder).join(User).filter(User.name == username)
	elif ltype == 'alphabeticalByName':
		query = query.order_by(Folder.name)
	elif ltype == 'alphabeticalByArtist':
		parent = aliased(Folder)
		query = query.join(parent, Folder.parent).order_by(parent.name).order_by(Folder.name)
	else:
		return request.error_formatter(0, 'Unknown search type')

	return request.formatter({
		'albumList': {
			'album': [ f.as_subsonic_child() for f in query.limit(size).offset(offset) ]
		}
	})

@app.route('/rest/getAlbumList2.view', methods = [ 'GET', 'POST' ])
def album_list_id3():
	username, ltype, size, offset = map(request.args.get, [ 'u', 'type', 'size', 'offset' ])
	try:
		size = int(size) if size else 10
		offset = int(offset) if offset else 0
	except:
		return request.error_formatter(0, 'Invalid parameter format')

	if not username:
		username = request.authorization.username

	query = Album.query
	if ltype == 'random':
		albums = query.all()
		return request.formatter({
			'albumList2': {
				'album': [ random.choice(albums).as_subsonic_album() for x in xrange(size) ]
			}
		})
	elif ltype == 'newest':
		query = query.join(Track, Album.tracks).group_by(Album.id).order_by(desc(func.min(Track.created)))
	elif ltype == 'frequent':
		query = query.join(Track, Album.tracks).group_by(Album.id).order_by(desc(func.sum(Track.play_count) / func.count()))
	elif ltype == 'recent':
		query = query.join(Track, Album.tracks).group_by(Album.id).order_by(desc(func.max(Track.last_play)))
	elif ltype == 'starred':
		query = query.join(StarredAlbum).join(User).filter(User.name == username)
	elif ltype == 'alphabeticalByName':
		query = query.order_by(Album.name)
	elif ltype == 'alphabeticalByArtist':
		query = query.join(Artist).order_by(Artist.name).order_by(Album.name)
	else:
		return request.error_formatter(0, 'Unknown search type')

	return request.formatter({
		'albumList2': {
			'album': [ f.as_subsonic_album() for f in query.limit(size).offset(offset) ]
		}
	})

@app.route('/rest/getNowPlaying.view', methods = [ 'GET', 'POST' ])
def now_playing():
	# SQLite specific
	query = User.query.join(Track).filter(func.strftime('%s', now()) - func.strftime('%s', User.last_play_date) < Track.duration * 2)
	return request.formatter({
		'nowPlaying': {
			'entry': [ dict(
				u.last_play.as_subsonic_child().items() +
				{ 'username': u.name, 'minutesAgo': (now() - u.last_play_date).seconds / 60, 'playerId': 0 }.items()
			) for u in query ]
		}
	})

@app.route('/rest/getStarred.view', methods = [ 'GET', 'POST' ])
def get_starred():
	username = request.args.get('u')
	if not username:
		username = request.authorization.username

	return request.formatter({
		'starred': {
			'artist': [ { 'id': sf.starred.name, 'name': sf.starred_id } for sf in StarredFolder.query.join(User).join(Folder).filter(User.name == username).filter(~ Folder.tracks.any()) ],
			'album': [ sf.starred.as_subsonic_child() for sf in StarredFolder.query.join(User).join(Folder).filter(User.name == username).filter(Folder.tracks.any()) ],
			'song': [ st.starred.as_subsonic_child() for st in StarredTrack.query.join(User).filter(User.name == username) ]
		}
	})

@app.route('/rest/getStarred2.view', methods = [ 'GET', 'POST' ])
def get_starred_id3():
	username = request.args.get('u')
	if not username:
		username = request.authorization.username

	return request.formatter({
		'starred2': {
			'artist': [ sa.starred.as_subsonic_artist() for sa in StarredArtist.query.join(User).filter(User.name == username) ],
			'album': [ sa.starred.as_subsonic_album() for sa in StarredAlbum.query.join(User).filter(User.name == username) ],
			'song': [ st.starred.as_subsonic_child() for st in StarredTrack.query.join(User).filter(User.name == username) ]
		}
	})


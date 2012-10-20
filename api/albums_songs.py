# coding: utf-8

from flask import request
from web import app
from db import Track
import random
import uuid

@app.route('/rest/getRandomSongs.view')
def rand_songs():
	size = request.args.get('size', '10')
	genre, fromYear, toYear, musicFolderId = map(request.args.get, [ 'genre', 'fromYear', 'toYear', 'musicFolderId' ])

	try:
		size = int(size) if size else 10
		fromYear = int(fromYear) if fromYear else None
		toYear = int(toYear) if toYear else None
		fid = uuid.UUID(musicFolderId) if musicFolderId else None
	except:
		return request.formatter({
			'error': {
				'code': 0,
				'message': 'Invalid parameter format'
			}
		}, error = True)

	query = Track.query
	if fromYear:
		query = query.filter(Track.year >= fromYear)
	if toYear:
		query = query.filter(Track.year <= toYear)
	if genre:
		query = query.filter(Track.genre == genre)
	if fid:
		query = query.filter(Track.folder_id == fid)
	tracks = query.all()

	if not tracks:
		return request.formatter({ 'randomSongs': {} })

	return request.formatter({
		'randomSongs': {
			'song': [ random.choice(tracks).as_subsonic_child() for x in xrange(size) ]
		}
	})


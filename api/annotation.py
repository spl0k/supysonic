# coding: utf-8

from time import time
import uuid
from flask import request
from web import app
from api import get_entity
from lastfm import LastFm
from db import *

@app.route('/rest/star.view', methods = [ 'GET', 'POST' ])
def star():
	id, albumId, artistId = map(request.args.getlist, [ 'id', 'albumId', 'artistId' ])

	def try_star(ent, starred_ent, eid):
		try:
			uid = uuid.UUID(eid)
		except:
			return 2, request.error_formatter(0, 'Invalid %s id' % ent.__name__)

		if starred_ent.query.filter(starred_ent.user_id == request.user.id).filter(starred_ent.starred_id == uid).first():
			return 2, request.error_formatter(0, '%s already starred' % ent.__name__)
		e = ent.query.get(uid)
		if e:
			session.add(starred_ent(user = request.user, starred = e))
		else:
			return 1, request.error_formatter(70, 'Unknown %s id' % ent.__name__)

		return 0, None

	for eid in id:
		err, ferror = try_star(Track, StarredTrack, eid)
		if err == 1:
			err, ferror = try_star(Folder, StarredFolder, eid)
			if err:
				return ferror
		elif err == 2:
			return ferror

	for alId in albumId:
		err, ferror = try_star(Album, StarredAlbum, alId)
		if err:
			return ferror

	for arId in artistId:
		err, ferror = try_star(Artist, StarredArtist, arId)
		if err:
			return ferror

	session.commit()
	return request.formatter({})

@app.route('/rest/unstar.view', methods = [ 'GET', 'POST' ])
def unstar():
	id, albumId, artistId = map(request.args.getlist, [ 'id', 'albumId', 'artistId' ])

	def try_unstar(ent, eid):
		try:
			uid = uuid.UUID(eid)
		except:
			return request.error_formatter(0, 'Invalid id')

		ent.query.filter(ent.user_id == request.user.id).filter(ent.starred_id == uid).delete()
		return None

	for eid in id:
		err = try_unstar(StarredTrack, eid)
		if err:
			return err
		err = try_unstar(StarredFolder, eid)
		if err:
			return err

	for alId in albumId:
		err = try_unstar(StarredAlbum, alId)
		if err:
			return err

	for arId in artistId:
		err = try_unstar(StarredArtist, arId)
		if err:
			return err

	session.commit()
	return request.formatter({})

@app.route('/rest/scrobble.view', methods = [ 'GET', 'POST' ])
def scrobble():
	status, res = get_entity(request, Track)
	if not status:
		return res

	t, submission = map(request.args.get, [ 'time', 'submission' ])

	if t:
		try:
			t = int(t) / 1000
		except:
			return request.error_formatter(0, 'Invalid time value')
	else:
		t = int(time())

	lfm = LastFm(request.user, app.logger)

	if submission in (None, '', True, 'true', 'True', 1, '1'):
		lfm.scrobble(res, t)
	else:
		lfm.now_playing(res)

	return request.formatter({})


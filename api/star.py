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
from web import app
from db import Track, StarredTrack, Album, StarredAlbum, Artist, StarredArtist, Folder, StarredFolder, session

@app.route('/rest/star.view', methods = [ 'GET', 'POST' ])
def star():
	id, albumId, artistId = map(request.args.getlist, [ 'id', 'albumId', 'artistId' ])

	def try_star(ent, starred_ent, eid):
		try:
			uid = uuid.UUID(eid)
		except:
			return 2, request.error_formatter(0, 'Invalid %s id' % ent.__name__)

		if starred_ent.query.get((request.user.id, uid)):
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


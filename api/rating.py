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

import uuid
from flask import request
from web import app
from db import RatingTrack, RatingFolder, Track, Folder, session

@app.route('/rest/setRating.view', methods = [ 'GET', 'POST' ])
def rate():
	id, rating = map(request.args.get, [ 'id', 'rating' ])
	if not id or not rating:
		return request.error_formatter(10, 'Missing parameter')

	try:
		uid = uuid.UUID(id)
		rating = int(rating)
	except:
		return request.error_formatter(0, 'Invalid parameter')

	if not rating in xrange(6):
		return request.error_formatter(0, 'rating must be between 0 and 5 (inclusive)')

	if rating == 0:
		RatingTrack.query.filter(RatingTrack.user_id == request.user.id).filter(RatingTrack.rated_id == uid).delete()
		RatingFolder.query.filter(RatingFolder.user_id == request.user.id).filter(RatingFolder.rated_id == uid).delete()
	else:
		rated = Track.query.get(uid)
		rating_ent = RatingTrack
		if not rated:
			rated = Folder.query.get(uid)
			rating_ent = RatingFolder
			if not rated:
				return request.error_formatter(70, 'Unknown id')

		rating_info = rating_ent.query.get((request.user.id, uid))
		if rating_info:
			rating_info.rating = rating
		else:
			session.add(rating_ent(user = request.user, rated = rated, rating = rating))

	session.commit()
	return request.formatter({})


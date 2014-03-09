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

import time
from flask import request
from web import app
from . import get_entity
from lastfm import LastFm
from db import Track

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
		t = int(time.time())

	lfm = LastFm(request.user, app.logger)

	if submission in (None, '', True, 'true', 'True', 1, '1'):
		lfm.scrobble(res, t)
	else:
		lfm.now_playing(res)

	return request.formatter({})


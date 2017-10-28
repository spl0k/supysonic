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
import uuid
from flask import request
from supysonic.web import app, store
from . import get_entity
from supysonic.lastfm import LastFm
from supysonic.db import Track, Album, Artist, Folder
from supysonic.db import StarredTrack, StarredAlbum, StarredArtist, StarredFolder
from supysonic.db import RatingTrack, RatingFolder

@app.route('/rest/star.view', methods = [ 'GET', 'POST' ])
def star():
    id, albumId, artistId = map(request.values.getlist, [ 'id', 'albumId', 'artistId' ])

    def try_star(ent, starred_ent, eid):
        try:
            uid = uuid.UUID(eid)
        except:
            return 2, request.error_formatter(0, 'Invalid %s id' % ent.__name__)

        if store.get(starred_ent, (request.user.id, uid)):
            return 2, request.error_formatter(0, '%s already starred' % ent.__name__)
        e = store.get(ent, uid)
        if e:
            starred = starred_ent()
            starred.user_id = request.user.id
            starred.starred_id = uid
            store.add(starred)
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

    store.commit()
    return request.formatter({})

@app.route('/rest/unstar.view', methods = [ 'GET', 'POST' ])
def unstar():
    id, albumId, artistId = map(request.values.getlist, [ 'id', 'albumId', 'artistId' ])

    def try_unstar(ent, eid):
        try:
            uid = uuid.UUID(eid)
        except:
            return request.error_formatter(0, 'Invalid id')

        store.find(ent, ent.user_id == request.user.id, ent.starred_id == uid).remove()
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

    store.commit()
    return request.formatter({})

@app.route('/rest/setRating.view', methods = [ 'GET', 'POST' ])
def rate():
    id, rating = map(request.values.get, [ 'id', 'rating' ])
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
        store.find(RatingTrack, RatingTrack.user_id == request.user.id, RatingTrack.rated_id == uid).remove()
        store.find(RatingFolder, RatingFolder.user_id == request.user.id, RatingFolder.rated_id == uid).remove()
    else:
        rated = store.get(Track, uid)
        rating_ent = RatingTrack
        if not rated:
            rated = store.get(Folder, uid)
            rating_ent = RatingFolder
            if not rated:
                return request.error_formatter(70, 'Unknown id')

        rating_info = store.get(rating_ent, (request.user.id, uid))
        if rating_info:
            rating_info.rating = rating
        else:
            rating_info = rating_ent()
            rating_info.user_id = request.user.id
            rating_info.rated_id = uid
            rating_info.rating = rating
            store.add(rating_info)

    store.commit()
    return request.formatter({})

@app.route('/rest/scrobble.view', methods = [ 'GET', 'POST' ])
def scrobble():
    status, res = get_entity(request, Track)
    if not status:
        return res

    t, submission = map(request.values.get, [ 'time', 'submission' ])

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


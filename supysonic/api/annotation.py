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

def try_star(ent, starred_ent, eid):
    """ Stars an entity

    :param ent: entity class, Folder, Artist, Album or Track
    :param starred_ent: class used for the db representation of the starring of ent
    :param eid: id of the entity to star
    :return error dict, if any. None otherwise
    """

    try:
        uid = uuid.UUID(eid)
    except:
        return { 'code': 0, 'message': 'Invalid {} id {}'.format(ent.__name__, eid) }

    if store.get(starred_ent, (request.user.id, uid)):
        return { 'code': 0, 'message': '{} {} already starred'.format(ent.__name__, eid) }

    e = store.get(ent, uid)
    if not e:
        return { 'code': 70, 'message': 'Unknown {} id {}'.format(ent.__name__, eid) }

    starred = starred_ent()
    starred.user_id = request.user.id
    starred.starred_id = uid
    store.add(starred)

    return None

def try_unstar(starred_ent, eid):
    """ Unstars an entity

    :param starred_ent: class used for the db representation of the starring of the entity
    :param eid: id of the entity to unstar
    :return error dict, if any. None otherwise
    """

    try:
        uid = uuid.UUID(eid)
    except:
        return { 'code': 0, 'message': 'Invalid id {}'.format(eid) }

    store.find(starred_ent, starred_ent.user_id == request.user.id, starred_ent.starred_id == uid).remove()
    return None

def merge_errors(errors):
    error = None
    errors = filter(None, errors)
    if len(errors) == 1:
        error = errors[0]
    elif len(errors) > 1:
        codes = set(map(lambda e: e['code'], errors))
        error = { 'code': list(codes)[0] if len(codes) == 1 else 0, 'error': errors }

    return error

@app.route('/rest/star.view', methods = [ 'GET', 'POST' ])
def star():
    id, albumId, artistId = map(request.values.getlist, [ 'id', 'albumId', 'artistId' ])

    if not id and not albumId and not artistId:
        return request.error_formatter(10, 'Missing parameter')

    errors = []
    for eid in id:
        terr = try_star(Track, StarredTrack, eid)
        ferr = try_star(Folder, StarredFolder, eid)
        if terr and ferr:
            errors += [ terr, ferr ]

    for alId in albumId:
        errors.append(try_star(Album, StarredAlbum, alId))

    for arId in artistId:
        errors.append(try_star(Artist, StarredArtist, arId))

    store.commit()
    error = merge_errors(errors)
    return request.formatter({ 'error': error }, error = True) if error else request.formatter({})

@app.route('/rest/unstar.view', methods = [ 'GET', 'POST' ])
def unstar():
    id, albumId, artistId = map(request.values.getlist, [ 'id', 'albumId', 'artistId' ])

    if not id and not albumId and not artistId:
        return request.error_formatter(10, 'Missing parameter')

    errors = []
    for eid in id:
        terr = try_unstar(StarredTrack, eid)
        ferr = try_unstar(StarredFolder, eid)
        if terr and ferr:
            errors += [ terr, ferr ]

    for alId in albumId:
        errors.append(try_unstar(StarredAlbum, alId))

    for arId in artistId:
        errors.append(try_unstar(StarredArtist, arId))

    store.commit()
    error = merge_errors(errors)
    return request.formatter({ 'error': error }, error = True) if error else request.formatter({})

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


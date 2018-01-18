# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2018  Alban 'spl0k' Féron
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

from flask import request, current_app as app
from pony.orm import db_session, delete
from pony.orm import ObjectNotFound

from ..db import Track, Album, Artist, Folder, User
from ..db import StarredTrack, StarredAlbum, StarredArtist, StarredFolder
from ..db import RatingTrack, RatingFolder
from ..lastfm import LastFm
from ..py23 import dict

from . import get_entity

@db_session
def try_star(cls, starred_cls, eid):
    """ Stars an entity

    :param cls: entity class, Folder, Artist, Album or Track
    :param starred_cls: class used for the db representation of the starring of ent
    :param eid: id of the entity to star
    :return error dict, if any. None otherwise
    """

    try:
        uid = uuid.UUID(eid)
    except:
        return dict(code = 0, message = 'Invalid {} id {}'.format(cls.__name__, eid))

    try:
        e = cls[uid]
    except ObjectNotFound:
        return dict(code = 70, message = 'Unknown {} id {}'.format(cls.__name__, eid))

    try:
        starred_cls[request.user.id, uid]
        return dict(code = 0, message = '{} {} already starred'.format(cls.__name__, eid))
    except ObjectNotFound:
        pass

    starred_cls(user = User[request.user.id], starred = e)
    return None

@db_session
def try_unstar(starred_cls, eid):
    """ Unstars an entity

    :param starred_cls: class used for the db representation of the starring of the entity
    :param eid: id of the entity to unstar
    :return error dict, if any. None otherwise
    """

    try:
        uid = uuid.UUID(eid)
    except:
        return dict(code = 0, message = 'Invalid id {}'.format(eid))

    delete(s for s in starred_cls if s.user.id == request.user.id and s.starred.id == uid)
    return None

def merge_errors(errors):
    error = None
    errors = [ e for e in errors if e ]
    if len(errors) == 1:
        error = errors[0]
    elif len(errors) > 1:
        codes = set(map(lambda e: e['code'], errors))
        error = dict(code = list(codes)[0] if len(codes) == 1 else 0, error = errors)

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

    error = merge_errors(errors)
    return request.formatter(dict(error = error), error = True) if error else request.formatter(dict())

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

    error = merge_errors(errors)
    return request.formatter(dict(error = error), error = True) if error else request.formatter(dict())

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

    if not 0 <= rating <= 5:
        return request.error_formatter(0, 'rating must be between 0 and 5 (inclusive)')

    with db_session:
        if rating == 0:
            delete(r for r in RatingTrack  if r.user.id == request.user.id and r.rated.id == uid)
            delete(r for r in RatingFolder if r.user.id == request.user.id and r.rated.id == uid)
        else:
            try:
                rated = Track[uid]
                rating_cls = RatingTrack
            except ObjectNotFound:
                try:
                    rated = Folder[uid]
                    rating_cls = RatingFolder
                except ObjectNotFound:
                    return request.error_formatter(70, 'Unknown id')

            try:
                rating_info = rating_cls[request.user.id, uid]
                rating_info.rating = rating
            except ObjectNotFound:
                rating_cls(user = User[request.user.id], rated = rated, rating = rating)

    return request.formatter(dict())

@app.route('/rest/scrobble.view', methods = [ 'GET', 'POST' ])
@db_session
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

    lfm = LastFm(app.config['LASTFM'], User[request.user.id], app.logger)

    if submission in (None, '', True, 'true', 'True', 1, '1'):
        lfm.scrobble(res, t)
    else:
        lfm.now_playing(res)

    return request.formatter(dict())


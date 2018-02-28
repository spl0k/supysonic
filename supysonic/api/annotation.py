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

import sys
import time
import uuid

from flask import current_app, request
from pony.orm import delete
from pony.orm import ObjectNotFound

from ..db import Track, Album, Artist, Folder, User
from ..db import StarredTrack, StarredAlbum, StarredArtist, StarredFolder
from ..db import RatingTrack, RatingFolder
from ..lastfm import LastFm
from ..py23 import dict

from . import api, get_entity
from .exceptions import AggregateException, GenericError, MissingParameter, NotFound

def star_single(cls, eid):
    """ Stars an entity

    :param cls: entity class, Folder, Artist, Album or Track
    :param eid: id of the entity to star
    """

    uid = uuid.UUID(eid)
    e = cls[uid]

    starred_cls = getattr(sys.modules[__name__], 'Starred' + cls.__name__)
    try:
        starred_cls[request.user, uid]
        raise GenericError('{} {} already starred'.format(cls.__name__, eid))
    except ObjectNotFound:
        pass

    starred_cls(user = request.user, starred = e)

def unstar_single(cls, eid):
    """ Unstars an entity

    :param cls: entity class, Folder, Artist, Album or Track
    :param eid: id of the entity to unstar
    """

    uid = uuid.UUID(eid)
    starred_cls = getattr(sys.modules[__name__], 'Starred' + cls.__name__)
    delete(s for s in starred_cls if s.user.id == request.user.id and s.starred.id == uid)
    return None

def handle_star_request(func):
    id, albumId, artistId = map(request.values.getlist, [ 'id', 'albumId', 'artistId' ])

    if not id and not albumId and not artistId:
        raise MissingParameter('id, albumId or artistId')

    errors = []
    for eid in id:
        terr = None
        ferr = None

        try:
            func(Track, eid)
        except Exception as e:
            terr = e
        try:
            func(Folder, eid)
        except Exception as e:
            ferr = e

        if terr and ferr:
            errors += [ terr, ferr ]

    for alId in albumId:
        try:
            func(Album, alId)
        except Exception as e:
            errors.append(e)

    for arId in artistId:
        try:
            func(Artist, arId)
        except Exception as e:
            errors.append(e)

    if errors:
        raise AggregateException(errors)
    return request.formatter.empty

@api.route('/star.view', methods = [ 'GET', 'POST' ])
def star():
    return handle_star_request(star_single)

@api.route('/unstar.view', methods = [ 'GET', 'POST' ])
def unstar():
    return handle_star_request(unstar_single)

@api.route('/setRating.view', methods = [ 'GET', 'POST' ])
def rate():
    id = request.values['id']
    rating = request.values['rating']

    uid = uuid.UUID(id)
    rating = int(rating)

    if not 0 <= rating <= 5:
        raise GenericError('rating must be between 0 and 5 (inclusive)')

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
                raise NotFound('Track or Folder')

        try:
            rating_info = rating_cls[request.user, uid]
            rating_info.rating = rating
        except ObjectNotFound:
            rating_cls(user = request.user, rated = rated, rating = rating)

    return request.formatter.empty

@api.route('/scrobble.view', methods = [ 'GET', 'POST' ])
def scrobble():
    res = get_entity(Track)
    t, submission = map(request.values.get, [ 'time', 'submission' ])
    t = int(t) / 1000 if t else int(time.time())

    lfm = LastFm(current_app.config['LASTFM'], request.user, current_app.logger)

    if submission in (None, '', True, 'true', 'True', 1, '1'):
        lfm.scrobble(res, t)
    else:
        lfm.now_playing(res)

    return request.formatter.empty


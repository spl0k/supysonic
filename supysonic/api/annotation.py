# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

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

from . import api, get_entity, get_entity_id
from .exceptions import AggregateException, GenericError, MissingParameter, NotFound


def star_single(cls, eid):
    """ Stars an entity

    :param cls: entity class, Folder, Artist, Album or Track
    :param eid: id of the entity to star
    """

    try:
        e = cls[eid]
    except ObjectNotFound:
        raise NotFound("{} {}".format(cls.__name__, eid))

    starred_cls = getattr(sys.modules[__name__], "Starred" + cls.__name__)
    try:
        starred_cls[request.user, eid]
        raise GenericError("{} {} already starred".format(cls.__name__, eid))
    except ObjectNotFound:
        pass

    starred_cls(user=request.user, starred=e)


def unstar_single(cls, eid):
    """ Unstars an entity

    :param cls: entity class, Folder, Artist, Album or Track
    :param eid: id of the entity to unstar
    """

    starred_cls = getattr(sys.modules[__name__], "Starred" + cls.__name__)
    delete(
        s for s in starred_cls if s.user.id == request.user.id and s.starred.id == eid
    )
    return None


def handle_star_request(func):
    id, albumId, artistId = map(request.values.getlist, ["id", "albumId", "artistId"])

    if not id and not albumId and not artistId:
        raise MissingParameter("id, albumId or artistId")

    errors = []
    for eid in id:
        try:
            tid = get_entity_id(Track, eid)
        except GenericError:
            tid = None
        try:
            fid = get_entity_id(Folder, eid)
        except GenericError:
            fid = None
        err = None

        if tid is None and fid is None:
            raise GenericError("Invalid ID")

        if tid is not None:
            try:
                func(Track, tid)
            except Exception as e:
                err = e
        else:
            try:
                func(Folder, fid)
            except Exception as e:
                err = e

        if err:
            errors.append(err)

    for alId in albumId:
        alb_id = get_entity_id(Album, alId)
        try:
            func(Album, alb_id)
        except Exception as e:
            errors.append(e)

    for arId in artistId:
        art_id = get_entity_id(Artist, arId)
        try:
            func(Artist, art_id)
        except Exception as e:
            errors.append(e)

    if errors:
        raise AggregateException(errors)
    return request.formatter.empty


@api.route("/star.view", methods=["GET", "POST"])
def star():
    return handle_star_request(star_single)


@api.route("/unstar.view", methods=["GET", "POST"])
def unstar():
    return handle_star_request(unstar_single)


@api.route("/setRating.view", methods=["GET", "POST"])
def rate():
    id = request.values["id"]
    rating = request.values["rating"]

    try:
        tid = get_entity_id(Track, id)
    except GenericError:
        tid = None
    try:
        fid = get_entity_id(Folder, id)
    except GenericError:
        fid = None
    uid = None
    rating = int(rating)

    if tid is None and fid is None:
        raise GenericError("Invalid ID")

    if not 0 <= rating <= 5:
        raise GenericError("rating must be between 0 and 5 (inclusive)")

    if rating == 0:
        if tid is not None:
            delete(
                r
                for r in RatingTrack
                if r.user.id == request.user.id and r.rated.id == tid
            )
        else:
            delete(
                r
                for r in RatingFolder
                if r.user.id == request.user.id and r.rated.id == fid
            )
    else:
        if tid is not None:
            rated = Track[tid]
            rating_cls = RatingTrack
            uid = tid
        else:
            rated = Folder[fid]
            rating_cls = RatingFolder
            uid = fid

        try:
            rating_info = rating_cls[request.user, uid]
            rating_info.rating = rating
        except ObjectNotFound:
            rating_cls(user=request.user, rated=rated, rating=rating)

    return request.formatter.empty


@api.route("/scrobble.view", methods=["GET", "POST"])
def scrobble():
    res = get_entity(Track)
    t, submission = map(request.values.get, ["time", "submission"])
    t = int(t) / 1000 if t else int(time.time())

    lfm = LastFm(current_app.config["LASTFM"], request.user)

    if submission in (None, "", True, "true", "True", 1, "1"):
        lfm.scrobble(res, t)
    else:
        lfm.now_playing(res)

    return request.formatter.empty

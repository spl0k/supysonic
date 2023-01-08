# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import time

from flask import current_app, request

from ..db import Track, Album, Artist, Folder
from ..db import StarredTrack, StarredAlbum, StarredArtist, StarredFolder
from ..db import RatingTrack, RatingFolder
from ..lastfm import LastFm

from . import get_entity, get_entity_id, api_routing
from .exceptions import AggregateException, GenericError, MissingParameter, NotFound


def star_single(cls, starcls, eid):
    """Stars an entity

    :param cls: entity class, Folder, Artist, Album or Track
    :param starcls: matching starred class, StarredFolder, StarredArtist, StarredAlbum or StarredTrack
    :param eid: id of the entity to star
    """

    try:
        e = cls[eid]
    except cls.DoesNotExist:
        raise NotFound(f"{cls.__name__} {eid}")

    try:
        starcls[request.user, eid]
        raise GenericError(f"{cls.__name__} {eid} already starred")
    except starcls.DoesNotExist:
        pass

    starcls.create(user=request.user, starred=e)


def unstar_single(cls, starcls, eid):
    """Unstars an entity

    :param cls: entity class, Folder, Artist, Album or Track
    :param starcls: matching starred class, StarredFolder, StarredArtist, StarredAlbum or StarredTrack
    :param eid: id of the entity to unstar
    """

    starcls.delete().where(
        starcls.user == request.user, starcls.starred == eid
    ).execute()


def handle_star_request(func):
    id, albumId, artistId = map(request.values.getlist, ("id", "albumId", "artistId"))

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
                func(Track, StarredTrack, tid)
            except Exception as e:
                err = e
        else:
            try:
                func(Folder, StarredFolder, fid)
            except Exception as e:
                err = e

        if err:
            errors.append(err)

    for alId in albumId:
        alb_id = get_entity_id(Album, alId)
        try:
            func(Album, StarredAlbum, alb_id)
        except Exception as e:
            errors.append(e)

    for arId in artistId:
        art_id = get_entity_id(Artist, arId)
        try:
            func(Artist, StarredArtist, art_id)
        except Exception as e:
            errors.append(e)

    if errors:
        raise AggregateException(errors)
    return request.formatter.empty


@api_routing("/star")
def star():
    return handle_star_request(star_single)


@api_routing("/unstar")
def unstar():
    return handle_star_request(unstar_single)


@api_routing("/setRating")
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
            RatingTrack.delete().where(
                RatingTrack.user == request.user, RatingTrack.rated == tid
            ).execute()
        else:
            RatingFolder.delete().where(
                RatingFolder.user == request.user, RatingFolder.rated == fid
            ).execute()
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
            rating_info.save()
        except rating_cls.DoesNotExist:
            rating_cls.create(user=request.user, rated=rated, rating=rating)

    return request.formatter.empty


@api_routing("/scrobble")
def scrobble():
    res = get_entity(Track)
    t, submission = map(request.values.get, ("time", "submission"))
    t = int(t) / 1000 if t else int(time.time())

    lfm = LastFm(current_app.config["LASTFM"], request.user)

    if submission in (None, "", True, "true", "True", 1, "1"):
        lfm.scrobble(res, t)
    else:
        lfm.now_playing(res)

    return request.formatter.empty

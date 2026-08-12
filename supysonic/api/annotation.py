# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import time

from flask import current_app, request

from ..db import (
    Album,
    Artist,
    Folder,
    RatingFolder,
    RatingTrack,
    StarredAlbum,
    StarredArtist,
    StarredFolder,
    StarredTrack,
    Track,
)
from ..lastfm import LastFm
from ..listenbrainz import ListenBrainz
from . import (
    MAX_TIMESTAMP_MS,
    api_routing,
    get_bool,
    get_entity,
    get_entity_id,
    get_int,
    resolve_child_id,
)
from .exceptions import AggregateException, GenericError, MissingParameter, NotFound

_STARRED_CLASSES = {Track: StarredTrack, Folder: StarredFolder}
_RATING_CLASSES = {Track: RatingTrack, Folder: RatingFolder}


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
        cls, rid = resolve_child_id(eid)
        try:
            func(cls, _STARRED_CLASSES[cls], rid)
        except Exception as e:
            errors.append(e)

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
    rating = get_int("rating", min=0, max=5, required=True)

    cls, rid = resolve_child_id(id)
    rating_cls = _RATING_CLASSES[cls]

    if rating == 0:
        rating_cls.delete().where(
            rating_cls.user == request.user, rating_cls.rated == rid
        ).execute()
    else:
        rated = cls[rid]
        try:
            rating_info = rating_cls[request.user, rid]
            rating_info.rating = rating
            rating_info.save()
        except rating_cls.DoesNotExist:
            rating_cls.create(user=request.user, rated=rated, rating=rating)

    return request.formatter.empty


@api_routing("/scrobble")
def scrobble():
    res = get_entity(Track)
    t = get_int("time", min=0, max=MAX_TIMESTAMP_MS)
    t = t / 1000 if t is not None else int(time.time())
    submission = get_bool("submission", True)

    lfm = LastFm(current_app.config["LASTFM"], request.user)
    lbz = ListenBrainz(current_app.config["LISTENBRAINZ"], request.user)

    if submission:
        lfm.scrobble(res, t)
        lbz.scrobble(res, t)
    else:
        lfm.now_playing(res)
        lbz.now_playing(res)

    return request.formatter.empty

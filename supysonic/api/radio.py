# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from ..db import RadioStation

from . import api, get_entity
from .exceptions import Forbidden, MissingParameter, NotFound


@api.route("/getInternetRadioStations.view", methods=["GET", "POST"])
def get_radio_stations():
    query = RadioStation.select().sort_by(RadioStation.name)
    return request.formatter(
        "internetRadioStations",
        dict(internetRadioStation=[p.as_subsonic_station() for p in query]),
    )


@api.route("/createInternetRadioStation.view", methods=["GET", "POST"])
def create_radio_station():
    if not request.user.admin:
        raise Forbidden()

    stream_url, name, homepage_url = map(
        request.values.get, ["streamUrl", "name", "homepageUrl"]
    )

    if stream_url and name:
        RadioStation(stream_url=stream_url, name=name, homepage_url=homepage_url)
    else:
        raise MissingParameter("streamUrl or name")

    return request.formatter.empty


@api.route("/updateInternetRadioStation.view", methods=["GET", "POST"])
def update_radio_station():
    if not request.user.admin:
        raise Forbidden()

    res = get_entity(RadioStation)

    stream_url, name, homepage_url = map(
        request.values.get, ["streamUrl", "name", "homepageUrl"]
    )
    if stream_url and name:
        res.stream_url = stream_url
        res.name = name

        if homepage_url:
            res.homepage_url = homepage_url
    else:
        raise MissingParameter("streamUrl or name")

    return request.formatter.empty


@api.route("/deleteInternetRadioStation.view", methods=["GET", "POST"])
def delete_radio_station():
    if not request.user.admin:
        raise Forbidden()

    res = get_entity(RadioStation)
    res.delete()

    return request.formatter.empty

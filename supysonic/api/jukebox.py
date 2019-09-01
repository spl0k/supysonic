# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from flask import current_app, request
from pony.orm import ObjectNotFound

from ..daemon import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError
from ..db import Track

from . import api
from .exceptions import GenericError, MissingParameter


@api.route("/jukeboxControl.view", methods=["GET", "POST"])
def jukebox_control():
    action = request.values["action"]

    index = request.values.get("index")
    offset = request.values.get("offset")
    id = request.values.getlist("id")
    gain = request.values.get("gain")

    if action not in (
        "get",
        "status",
        "set",
        "start",
        "stop",
        "skip",
        "add",
        "clear",
        "remove",
        "shuffle",
        "setGain",
    ):
        raise GenericError("Unknown action")

    arg = None
    if action == "set":
        if not id:
            arg = []
        else:
            arg = [uuid.UUID(i) for i in id]
    elif action == "skip":
        if not index:
            raise MissingParameter("index")
        else:
            arg = int(index)
    elif action == "add":
        if not id:
            raise MissingParameter("id")
        else:
            arg = [uuid.UUID(i) for i in id]
    elif action == "remove":
        if not index:
            raise MissingParameter("index")
        else:
            arg = int(index)
    elif action == "setGain":
        if not gain:
            raise MissingParameter("gain")
        else:
            arg = float(gain)

    try:
        status = DaemonClient(current_app.config["DAEMON"]["socket"]).jukebox_control(
            action, arg
        )
    except DaemonUnavailableError:
        raise GenericError("Jukebox unavaliable")

    rv = dict(currentIndex=status.index, playing=status.playing, gain=status.gain)
    if action == "get":
        playlist = []
        for path in status.playlist:
            try:
                playlist.append(Track.get(path=path))
            except ObjectNotFound:
                pass
        rv["entry"] = [
            t.as_subsonic_child(request.user, request.client) for t in playlist
        ]
        return request.formatter("jukeboxPlaylist", rv)
    else:
        return request.formatter("jukeboxStatus", rv)

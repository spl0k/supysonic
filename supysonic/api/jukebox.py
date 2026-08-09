# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from flask import current_app, request

from ..daemon import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError
from ..db import SerializationContext, Track
from . import api_routing, get_float, get_int
from .exceptions import Forbidden, GenericError, MissingParameter


@api_routing("/jukeboxControl")
def jukebox_control():
    if not request.user.jukebox and not request.user.admin:
        raise Forbidden()

    action = request.values["action"]

    index = get_int("index", min=0)
    offset = get_int("offset", min=0)
    id = request.values.getlist("id")
    gain = get_float("gain", min=0, max=1)

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

    args = ()
    if action == "set":
        if id:
            args = [uuid.UUID(i) for i in id]
    elif action == "skip":
        if index is None:
            raise MissingParameter("index")
        args = (index, offset or 0)
    elif action == "add":
        if not id:
            raise MissingParameter("id")
        else:
            args = [uuid.UUID(i) for i in id]
    elif action == "remove":
        if index is None:
            raise MissingParameter("index")
        args = (index,)
    elif action == "setGain":
        if gain is None:
            raise MissingParameter("gain")
        args = (gain,)

    try:
        status = DaemonClient(current_app.config["DAEMON"]["socket"]).jukebox_control(
            action, *args
        )
    except DaemonUnavailableError:
        raise GenericError("Jukebox unavaliable")

    rv = {
        "currentIndex": status.index,
        "playing": status.playing,
        "gain": status.gain,
        "position": status.position,
    }
    if action == "get":
        playlist = []
        for path in status.playlist:
            try:
                playlist.append(Track.get(path=path))
            except Track.DoesNotExist:
                pass
        ctx = SerializationContext(request.user, request.client)
        ctx.add_tracks(playlist)
        rv["entry"] = [t.as_subsonic_child(ctx) for t in playlist]
        return request.formatter("jukeboxPlaylist", rv)
    else:
        return request.formatter("jukeboxStatus", rv)

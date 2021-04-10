# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from flask import Response, flash, redirect, render_template, request, url_for
from pony.orm import ObjectNotFound

from ..db import Playlist

from . import frontend


@frontend.route("/playlist")
def playlist_index():
    return render_template(
        "playlists.html",
        mine=Playlist.select(lambda p: p.user == request.user),
        others=Playlist.select(lambda p: p.user != request.user and p.public),
    )


@frontend.route("/playlist/<uid>")
def playlist_details(uid):
    try:
        uid = uuid.UUID(uid)
    except ValueError:
        flash("Invalid playlist id")
        return redirect(url_for("frontend.playlist_index"))

    try:
        playlist = Playlist[uid]
    except ObjectNotFound:
        flash("Unknown playlist")
        return redirect(url_for("frontend.playlist_index"))

    return render_template("playlist.html", playlist=playlist)


@frontend.route("/playlist/<uid>/export")
def playlist_export(uid):
    try:
        uid = uuid.UUID(uid)
    except ValueError:
        flash("Invalid playlist id")
        return redirect(url_for("frontend.playlist_index"))

    try:
        playlist = Playlist[uid]
    except ObjectNotFound:
        flash("Unknown playlist")
        return redirect(url_for("frontend.playlist_index"))

    return Response(
        render_template("playlist_export.m3u", playlist=playlist),
        mimetype="audio/mpegurl",
        headers={
            "Content-disposition": "attachment; filename={}.m3u".format(playlist.name)
        },
    )


@frontend.route("/playlist/<uid>", methods=["POST"])
def playlist_update(uid):
    try:
        uid = uuid.UUID(uid)
    except ValueError:
        flash("Invalid playlist id")
        return redirect(url_for("frontend.playlist_index"))

    try:
        playlist = Playlist[uid]
    except ObjectNotFound:
        flash("Unknown playlist")
        return redirect(url_for("frontend.playlist_index"))

    if playlist.user.id != request.user.id:
        flash("You're not allowed to edit this playlist")
    elif not request.form.get("name"):
        flash("Missing playlist name")
    else:
        playlist.name = request.form.get("name")
        playlist.public = request.form.get("public") in (
            True,
            "True",
            1,
            "1",
            "on",
            "checked",
        )
        flash("Playlist updated.")

    return playlist_details(str(uid))


@frontend.route("/playlist/del/<uid>")
def playlist_delete(uid):
    try:
        uid = uuid.UUID(uid)
    except ValueError:
        flash("Invalid playlist id")
        return redirect(url_for("frontend.playlist_index"))

    try:
        playlist = Playlist[uid]
    except ObjectNotFound:
        flash("Unknown playlist")
        return redirect(url_for("frontend.playlist_index"))

    if playlist.user.id != request.user.id:
        flash("You're not allowed to delete this playlist")
    else:
        playlist.delete()
        flash("Playlist deleted")

    return redirect(url_for("frontend.playlist_index"))

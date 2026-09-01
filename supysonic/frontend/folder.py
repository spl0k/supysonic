# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import current_app, flash, redirect, render_template, request, url_for

from ..app.flask import app_layer
from ..daemon.exceptions import DaemonUnavailableError
from ..db import Folder
from ._blueprint import frontend
from ._helpers import admin_only


@frontend.get("/folder")
@admin_only
def folder_index():
    try:
        app_layer.daemon.get_scanning_progress()
        allow_scan = True
    except DaemonUnavailableError:
        allow_scan = False
        flash(
            "The daemon is unavailable, can't scan from the web interface, use the CLI to do so.",
            "warning",
        )
    return render_template(
        "folders.html",
        folders=Folder.select().where(Folder.root),
        allow_scan=allow_scan,
    )


@frontend.get("/folder/add")
@admin_only
def add_folder_form():
    return render_template("addfolder.html")


@frontend.post("/folder/add")
@admin_only
def add_folder_post():
    error = False
    name, path = map(request.form.get, ("name", "path"))
    if name in (None, ""):
        flash("The name is required.", "danger")
        error = True
    if path in (None, ""):
        flash("The path is required.", "danger")
        error = True
    if error:
        return render_template("addfolder.html")

    try:
        app_layer.folders.add(name, path)
    except ValueError as e:
        flash(str(e), "danger")
        return render_template("addfolder.html")

    flash(f"Folder '{name}' created. You should now run a scan", "success")
    return redirect(url_for("frontend.folder_index"))


@frontend.post("/folder/del/<id>")
@admin_only
def del_folder(id):
    try:
        app_layer.folders.delete(id)
        flash("Deleted folder", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Folder.DoesNotExist:
        flash("No such folder", "danger")

    return redirect(url_for("frontend.folder_index"))


@frontend.post("/folder/scan")
@frontend.post("/folder/scan/<id>")
@admin_only
def scan_folder(id=None):
    try:
        if id is not None:
            folders = [app_layer.folders.get(id).name]
        else:
            folders = []
        app_layer.daemon.scan(folders)
        flash("Scanning started")
    except ValueError as e:
        flash(str(e), "danger")
    except Folder.DoesNotExist:
        flash("No such folder", "danger")
    except DaemonUnavailableError:
        flash("Can't start scan", "danger")

    return redirect(url_for("frontend.folder_index"))

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import current_app, flash, redirect, render_template, request, url_for

from ..daemon.client import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError
from ..db import Folder
from ..managers.folder import FolderManager

from . import admin_only, frontend


@frontend.route("/folder")
@admin_only
def folder_index():
    try:
        DaemonClient(current_app.config["DAEMON"]["socket"]).get_scanning_progress()
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


@frontend.route("/folder/add")
@admin_only
def add_folder_form():
    return render_template("addfolder.html")


@frontend.route("/folder/add", methods=["POST"])
@admin_only
def add_folder_post():
    error = False
    name, path = map(request.form.get, ("name", "path"))
    if name in (None, ""):
        flash("The name is required.")
        error = True
    if path in (None, ""):
        flash("The path is required.")
        error = True
    if error:
        return render_template("addfolder.html")

    try:
        FolderManager.add(name, path)
    except ValueError as e:
        flash(str(e), "error")
        return render_template("addfolder.html")

    flash(f"Folder '{name}' created. You should now run a scan")
    return redirect(url_for("frontend.folder_index"))


@frontend.route("/folder/del/<id>")
@admin_only
def del_folder(id):
    try:
        FolderManager.delete(id)
        flash("Deleted folder")
    except ValueError as e:
        flash(str(e), "error")
    except Folder.DoesNotExist:
        flash("No such folder", "error")

    return redirect(url_for("frontend.folder_index"))


@frontend.route("/folder/scan")
@frontend.route("/folder/scan/<id>")
@admin_only
def scan_folder(id=None):
    try:
        if id is not None:
            folders = [FolderManager.get(id).name]
        else:
            folders = []
        DaemonClient(current_app.config["DAEMON"]["socket"]).scan(folders)
        flash("Scanning started")
    except ValueError as e:
        flash(str(e), "error")
    except Folder.DoesNotExist:
        flash("No such folder", "error")
    except DaemonUnavailableError:
        flash("Can't start scan", "error")

    return redirect(url_for("frontend.folder_index"))

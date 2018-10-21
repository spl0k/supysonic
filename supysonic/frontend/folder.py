# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import base64
import os.path
import pickle
import uuid

from flask import current_app, flash, redirect, render_template, request, url_for
from pony.orm import ObjectNotFound

from ..db import Folder,Meta
from ..managers.folder import FolderManager
from ..scanner import Scanner
from ..scanner_master import ScannerClient

from . import admin_only, frontend

@frontend.route('/folder')
@admin_only
def folder_index():
    return render_template('folders.html', folders = Folder.select(lambda f: f.root))

@frontend.route('/folder/add')
@admin_only
def add_folder_form():
    return render_template('addfolder.html')

@frontend.route('/folder/add', methods = [ 'POST' ])
@admin_only
def add_folder_post():
    error = False
    (name, path) = map(request.form.get, [ 'name', 'path' ])
    if name in (None, ''):
        flash('The name is required.')
        error = True
    if path in (None, ''):
        flash('The path is required.')
        error = True
    if error:
        return render_template('addfolder.html')

    try:
        FolderManager.add(name, path)
    except ValueError as e:
        flash(str(e), 'error')
        return render_template('addfolder.html')

    flash("Folder '%s' created. You should now run a scan" % name)
    return redirect(url_for('frontend.folder_index'))

@frontend.route('/folder/del/<id>')
@admin_only
def del_folder(id):
    try:
        FolderManager.delete(id)
        flash('Deleted folder')
    except ValueError as e:
        flash(str(e), 'error')
    except ObjectNotFound:
        flash('No such folder', 'error')

    return redirect(url_for('frontend.folder_index'))

@frontend.route('/folder/scan')
@frontend.route('/folder/scan/<id>')
@admin_only
def scan_folder(id = None):
    extensions = current_app.config['BASE']['scanner_extensions']
    if extensions:
        extensions = extensions.split(' ')

    scanner = Scanner(extensions = extensions)

    if id is None:
        folders = (folder.id for folder in Folder.select(lambda f: f.root))
    else:
        try:
            folders = [FolderManager.get(id).id]
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('frontend.folder_index'))
        except ObjectNotFound:
            flash('No such folder', 'error')
            return redirect(url_for('frontend.folder_index'))

    sc =  ScannerClient(pickle.loads(base64.b64decode(Meta['scanner_location'].value)))
    sc.scan(*folders)
    sc.close()

    flash('Added to scanning queue')
    return redirect(url_for('frontend.folder_index'))


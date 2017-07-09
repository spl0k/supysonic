# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from flask import request, flash, render_template, redirect, url_for, session
import os.path
import uuid

from supysonic.web import app, store
from supysonic.db import Folder
from supysonic.scanner import Scanner
from supysonic.managers.user import UserManager
from supysonic.managers.folder import FolderManager

@app.before_request
def check_admin():
	if not request.path.startswith('/folder'):
		return

	if not UserManager.get(store, session.get('userid'))[1].admin:
		return redirect(url_for('index'))

@app.route('/folder')
def folder_index():
	return render_template('folders.html', folders = store.find(Folder, Folder.root == True), admin = UserManager.get(store, session.get('userid'))[1].admin)

@app.route('/folder/add', methods = [ 'GET', 'POST' ])
def add_folder():
	if request.method == 'GET':
		return render_template('addfolder.html', admin = UserManager.get(store, session.get('userid'))[1].admin)

	error = False
	(name, path) = map(request.form.get, [ 'name', 'path' ])
	if name in (None, ''):
		flash('The name is required.')
		error = True
	if path in (None, ''):
		flash('The path is required.')
		error = True
	if error:
		return render_template('addfolder.html', admin = UserManager.get(store, session.get('userid'))[1].admin)

	ret = FolderManager.add(store, name, path)
	if ret != FolderManager.SUCCESS:
		flash(FolderManager.error_str(ret))
		return render_template('addfolder.html', admin = UserManager.get(store, session.get('userid'))[1].admin)

	flash("Folder '%s' created. You should now run a scan" % name)

	return redirect(url_for('folder_index'))

@app.route('/folder/del/<id>')
def del_folder(id):
	try:
		idid = uuid.UUID(id)
	except ValueError:
		flash('Invalid folder id')
		return redirect(url_for('folder_index'))

	ret = FolderManager.delete(store, idid)
	if ret != FolderManager.SUCCESS:
		flash(FolderManager.error_str(ret))
	else:
		flash('Deleted folder')

	return redirect(url_for('folder_index'))

@app.route('/folder/scan')
@app.route('/folder/scan/<id>')
def scan_folder(id = None):
	scanner = Scanner(store)
	if id is None:
		for folder in store.find(Folder, Folder.root == True):
			scanner.scan(folder)
	else:
		status, folder = FolderManager.get(store, id)
		if status != FolderManager.SUCCESS:
			flash(FolderManager.error_str(status))
			return redirect(url_for('folder_index'))
		scanner.scan(folder)

	scanner.finish()
	added, deleted = scanner.stats()
	store.commit()

	flash('Added: %i artists, %i albums, %i tracks' % (added[0], added[1], added[2]))
	flash('Deleted: %i artists, %i albums, %i tracks' % (deleted[0], deleted[1], deleted[2]))
	return redirect(url_for('folder_index'))


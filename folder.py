# coding: utf-8

from flask import request, flash, render_template, redirect, url_for
import os.path
import uuid

from web import app
from db import session, Folder, Artist
from scanner import Scanner

@app.route('/folder')
def folder_index():
	return render_template('folders.html', folders = Folder.query.filter(Folder.root == True).all())

@app.route('/folder/add', methods = [ 'GET', 'POST' ])
def add_folder():
	if request.method == 'GET':
		return render_template('addfolder.html')

	error = False
	(name, path) = map(request.form.get, [ 'name', 'path' ])
	if name in (None, ''):
		flash('The name is required.')
		error = True
	elif Folder.query.filter(Folder.name == name and Folder.root).first():
		flash('There is already a folder with that name. Please pick another one.')
		error = True
	if path in (None, ''):
		flash('The path is required.')
		error = True
	else:
		path = os.path.abspath(path)
		if not os.path.isdir(path):
			flash("The path '%s' doesn't exists or isn't a directory" % path)
			error = True
		folder = Folder.query.filter(Folder.path == path).first()
		if folder:
			flash("This path is already registered")
			error = True
	if error:
		return render_template('addfolder.html')

	folder = Folder(root = True, name = name, path = path)
	session.add(folder)
	session.commit()
	flash("Folder '%s' created. You should now run a scan" % name)

	return redirect(url_for('folder_index'))

@app.route('/folder/del/<id>')
def del_folder(id):
	try:
		idid = uuid.UUID(id)
	except ValueError:
		flash('Invalid folder id')
		return redirect(url_for('folder_index'))

	folder = Folder.query.get(idid)
	if folder is None or not folder.root:
		flash('No such folder')
		return redirect(url_for('folder_index'))

	# delete associated tracks and prune empty albums/artists
	for artist in Artist.query.all():
		for album in artist.albums[:]:
			for track in filter(lambda t: t.root_folder.id == folder.id, album.tracks):
				album.tracks.remove(track)
				session.delete(track)
			if len(album.tracks) == 0:
				artist.albums.remove(album)
				session.delete(album)
		if len(artist.albums) == 0:
			session.delete(artist)

	def cleanup_folder(folder):
		for f in folder.children:
			cleanup_folder(f)
		session.delete(folder)

	cleanup_folder(folder)

	session.commit()
	flash("Deleted folder '%s'" % folder.name)

	return redirect(url_for('folder_index'))

@app.route('/folder/scan')
@app.route('/folder/scan/<id>')
def scan_folder(id = None):
	s = Scanner(session)
	if id is None:
		for folder in Folder.query.filter(Folder.root == True).all():
			s.scan(folder)
			s.prune(folder)
			s.check_cover_art(folder)
	else:
		try:
			idid = uuid.UUID(id)
		except ValueError:
			flash('Invalid folder id')
			return redirect(url_for('folder_index'))

		folder = Folder.query.get(idid)
		if folder is None or not folder.root:
			flash('No such folder')
			return redirect(url_for('folder_index'))

		s.scan(folder)
		s.prune(folder)
		s.check_cover_art(folder)

	added, deleted = s.stats()
	session.commit()

	flash('Added: %i artists, %i albums, %i tracks' % (added[0], added[1], added[2]))
	flash('Deleted: %i artists, %i albums, %i tracks' % (deleted[0], deleted[1], deleted[2]))
	return redirect(url_for('folder_index'))


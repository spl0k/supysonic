# coding: utf-8

from flask import Flask, request, session, flash, render_template, redirect, url_for
import os.path
import uuid

app = Flask(__name__)
app.secret_key = '?9huDM\\H'

import db
from scanner import Scanner

@app.before_request
def init_and_login_check():
	if request.path.startswith('/rest/'):
		return

	admin_count = db.User.query.filter(db.User.admin == True).count()
	if admin_count == 0 and request.endpoint != 'add_user':
		flash('Not configured. Please create the first admin user')
		return redirect(url_for('add_user'))

	if not (admin_count == 0 and request.endpoint == 'add_user') and not session.get('userid') and request.endpoint != 'login':
		flash('Please login')
		return redirect(url_for('login', returnUrl = request.url[len(request.url_root)-1:]))

@app.teardown_request
def teardown(exception):
	db.session.remove()

@app.route('/')
def index():
	return render_template('home.html', folders = db.Folder.query.filter(db.Folder.root == True).all(),
		artists = db.Artist.query.order_by(db.Artist.name).all(),
		albums = db.Album.query.join(db.Album.artist).order_by(db.Artist.name, db.Album.name).all())

@app.route('/resetdb')
def reset_db():
	db.recreate_db()
	return redirect(url_for('index'))

@app.route('/addfolder', methods = [ 'GET', 'POST' ])
def add_folder():
	if request.method == 'GET':
		return render_template('addfolder.html')

	error = False
	(name, path) = map(request.form.get, [ 'name', 'path' ])
	if name in (None, ''):
		flash('The name is required.')
		error = True
	elif db.Folder.query.filter(db.Folder.name == name and db.Folder.root).first():
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
		folder = db.Folder.query.filter(db.Folder.path == path).first()
		if folder:
			flash("This path is already registered")
			error = True
	if error:
		return render_template('addfolder.html')

	folder = db.Folder(root = True, name = name, path = path)
	db.session.add(folder)
	db.session.commit()
	flash("Folder '%s' created. You should now run a scan" % name)

	return redirect(url_for('index'))

@app.route('/delfolder/<id>')
def del_folder(id):
	try:
		idid = uuid.UUID(id)
	except ValueError:
		flash('Invalid folder id')
		return redirect(url_for('index'))

	folder = db.Folder.query.get(idid)
	if folder is None:
		flash('No such folder')
		return redirect(url_for('index'))

	# delete associated tracks and prune empty albums/artists
	for artist in db.Artist.query.all():
		for album in artist.albums[:]:
			for track in filter(lambda t: t.root_folder.id == folder.id, album.tracks):
				album.tracks.remove(track)
				db.session.delete(track)
			if len(album.tracks) == 0:
				artist.albums.remove(album)
				db.session.delete(album)
		if len(artist.albums) == 0:
			db.session.delete(artist)

	def cleanup_folder(folder):
		for f in folder.children:
			cleanup_folder(f)
		db.session.delete(folder)

	cleanup_folder(folder)

	db.session.commit()
	flash("Deleted folder '%s'" % folder.name)

	return redirect(url_for('index'))

@app.route('/scan')
@app.route('/scan/<id>')
def scan_folder(id = None):
	s = Scanner(db.session)
	if id is None:
		for folder in db.Folder.query.filter(db.Folder.root == True).all():
			s.scan(folder)
			s.prune(folder)
			s.check_cover_art(folder)
	else:
		try:
			idid = uuid.UUID(id)
		except ValueError:
			flash('Invalid folder id')
			return redirect(url_for('index'))

		folder = db.Folder.query.get(idid)
		if folder is None or not folder.root:
			flash('No such folder')
			return redirect(url_for('index'))

		s.scan(folder)
		s.prune(folder)
		s.check_cover_art(folder)

	added, deleted = s.stats()
	db.session.commit()

	flash('Added: %i artists, %i albums, %i tracks' % (added[0], added[1], added[2]))
	flash('Deleted: %i artists, %i albums, %i tracks' % (deleted[0], deleted[1], deleted[2]))
	return redirect(url_for('index'))

import user

import api.system
import api.browse
import api.user
import api.albums_songs
import api.media


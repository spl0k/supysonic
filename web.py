# coding: utf-8

from flask import Flask, request, flash, render_template, redirect, url_for
from sqlalchemy.orm.exc import NoResultFound
import string, random, hashlib
import os.path
import uuid

app = Flask(__name__)
app.secret_key = '?9huDM\\H'

import db
from scanner import Scanner

@app.teardown_request
def teardown(exception):
	db.session.remove()

@app.route('/')
def index():
	"""
	if User.query.count() == 0:
		flash('Not configured. Please create the first admin user')
		return redirect(url_for('add_user'))
	"""
	return render_template('home.html', users = db.User.query.all(), folders = db.MusicFolder.query.all(),
		artists = db.Artist.query.order_by(db.Artist.name).all(),
		albums = db.Album.query.join(db.Album.artist).order_by(db.Artist.name, db.Album.name).all(),
		tracks = db.Track.query.join(db.Track.album, db.Album.artist).order_by(db.Artist.name, db.Album.name, db.Track.disc, db.Track.number).all())

@app.route('/resetdb')
def reset_db():
	db.recreate_db()
	return redirect(url_for('index'))

@app.route('/adduser', methods = [ 'GET', 'POST' ])
def add_user():
	if request.method == 'GET':
		return render_template('adduser.html')

	error = False
	(name, passwd, passwd_confirm, mail) = map(request.form.get, [ 'name', 'passwd', 'passwd_confirm', 'mail' ])
	if name in (None, ''):
		flash('The name is required.')
		error = True
	elif db.User.query.filter(db.User.name == name).first():
		flash('There is already a user with that name. Please pick another one.')
		error = True
	if passwd in (None, ''):
		flash('Please provide a password.')
		error = True
	elif passwd != passwd_confirm:
		flash("The passwords don't match.")
		error = True
	if error:
		return render_template('adduser.html')

	salt = ''.join(random.choice(string.printable.strip()) for i in xrange(6))
	crypt = hashlib.sha1(salt + passwd).hexdigest()
	user = db.User(name = name, mail = mail, password = crypt, salt = salt)
	db.session.add(user)
	db.session.commit()
	flash("User '%s' successfully added" % name)

	return redirect(url_for('index'))

@app.route('/deluser/<id>')
def del_user(id):
	try:
		idid = uuid.UUID(id)
	except ValueError:
		flash('Invalid user id')
		return redirect(url_for('index'))

	user = db.User.query.get(idid)
	if user is None:
		flash('No such user')
		return redirect(url_for('index'))

	db.session.delete(user)
	db.session.commit()
	flash("Deleted user '%s'" % user.name)

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
	elif db.MusicFolder.query.filter(db.MusicFolder.name == name).first():
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
		folder = db.MusicFolder.query.filter(db.MusicFolder.name == name).first()
		if folder:
			flash("This path is already registered with the name '%s'" % folder.name)
			error = True
	if error:
		return render_template('addfolder.html')

	folder = db.MusicFolder(name = name, path = path)
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

	folder = db.MusicFolder.query.get(idid)
	if folder is None:
		flash('No such folder')
		return redirect(url_for('index'))

	# delete associated tracks and prune empty albums/artists
	for artist in db.Artist.query.all():
		for album in artist.albums[:]:
			for track in filter(lambda t: t.folder.id == folder.id, album.tracks):
				album.tracks.remove(track)
				db.session.delete(track)
			if len(album.tracks) == 0:
				artist.albums.remove(album)
				db.session.delete(album)
		if len(artist.albums) == 0:
			db.session.delete(artist)
	db.session.delete(folder)

	db.session.commit()
	flash("Deleted folder '%s'" % folder.name)

	return redirect(url_for('index'))

@app.route('/scan')
@app.route('/scan/<id>')
def scan_folder(id = None):
	s = Scanner(db.session)
	if id is None:
		for folder in db.MusicFolder.query.all():
			s.scan(folder)
			s.prune(folder)
	else:
		try:
			idid = uuid.UUID(id)
		except ValueError:
			flash('Invalid folder id')
			return redirect(url_for('index'))

		folder = db.MusicFolder.query.get(idid)
		if folder is None:
			flash('No such folder')
			return redirect(url_for('index'))

		s.scan(folder)
		s.prune(folder)

	added, deleted = s.stats()
	db.session.commit()

	flash('Added: %i artists, %i albums, %i tracks' % (added[0], added[1], added[2]))
	flash('Deleted: %i artists, %i albums, %i tracks' % (deleted[0], deleted[1], deleted[2]))
	return redirect(url_for('index'))

import api.system
import api.browse
import api.user
import api.albums_songs
import api.media


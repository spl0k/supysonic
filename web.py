# coding: utf-8

from flask import Flask, request, session, flash, render_template, redirect, url_for

app = Flask(__name__)
app.secret_key = '?9huDM\\H'

import db
from user_manager import UserManager

@app.before_request
def init_and_login_check():
	if request.path.startswith('/rest/'):
		return

	admin_count = db.User.query.filter(db.User.admin == True).count()
	if admin_count == 0 and request.endpoint != 'add_user':
		flash('Not configured. Please create the first admin user')
		return redirect(url_for('add_user'))

	if not (admin_count == 0 and request.endpoint == 'add_user') and request.endpoint != 'login':
		should_login = False
		if not session.get('userid'):
			should_login = True
		elif UserManager.get(session.get('userid'))[0] != UserManager.SUCCESS:
			session.clear()
			should_login = True

		if should_login:
			flash('Please login')
			return redirect(url_for('login', returnUrl = request.url[len(request.url_root)-1:]))

@app.teardown_request
def teardown(exception):
	db.session.remove()

@app.route('/')
def index():
	return render_template('home.html',
		artists = db.Artist.query.order_by(db.Artist.name).all(),
		albums = db.Album.query.join(db.Album.artist).order_by(db.Artist.name, db.Album.name).all())

@app.route('/resetdb')
def reset_db():
	db.recreate_db()
	return redirect(url_for('index'))

import user
import folder

import api.system
import api.browse
import api.user
import api.albums_songs
import api.media


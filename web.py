# coding: utf-8

from flask import Flask, request, flash, render_template, redirect, url_for
import string, random, hashlib
import os.path

app = Flask(__name__)
app.secret_key = '?9huDM\\H'

from db import db_session
from db import User, MusicFolder

@app.teardown_request
def teardown(exception):
	db_session.remove()

@app.route('/')
def index():
	"""
	if User.query.count() == 0:
		flash('Not configured. Please create the first admin user')
		return redirect(url_for('add_user'))
	"""
	return render_template('home.html', users = User.query.all(), folders = MusicFolder.query.all())

@app.route('/adduser', methods = [ 'GET', 'POST' ])
def add_user():
	if request.method == 'GET':
		return render_template('adduser.html')

	error = False
	(name, passwd, passwd_confirm, mail) = map(request.form.get, [ 'name', 'passwd', 'passwd_confirm', 'mail' ])
	if name in (None, ''):
		flash('The name is required.')
		error = True
	elif User.query.filter(User.name == name).first():
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
	user = User(name = name, mail = mail, password = crypt, salt = salt)
	db_session.add(user)
	db_session.commit()
	flash("User '%s' successfully added" % name)

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
	elif MusicFolder.query.filter(MusicFolder.name == name).first():
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
		folder = MusicFolder.query.filter(MusicFolder.name == name).first()
		if folder:
			flash("This path is already registered with the name '%s'" % folder.name)
			error = True
	if error:
		return render_template('addfolder.html')

	folder = MusicFolder(name = name, path = path)
	db_session.add(folder)
	db_session.commit()
	flash("Folder '%s' created. You should now run a scan" % name)

	return redirect(url_for('index'))

import api.system
import api.browse


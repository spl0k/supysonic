# coding: utf-8

from flask import Flask, request, flash, render_template, redirect, url_for
from sqlalchemy.orm.exc import NoResultFound
import string, random, hashlib
import os.path
import uuid

app = Flask(__name__)
app.secret_key = '?9huDM\\H'

import db

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
	return render_template('home.html', users = db.User.query.all(), folders = db.MusicFolder.query.all())

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
		user = db.User.query.filter(db.User.id == uuid.UUID(id)).one()
		db.session.delete(user)
		db.session.commit()
		flash("Deleted user '%s'" % user.name)
	except ValueError:
		flash('Invalid user id')
	except NoResultFound:
		flash('No such user')

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
		folder = db.MusicFolder.query.filter(db.MusicFolder.id == uuid.UUID(id)).one()
		db.session.delete(folder)
		db.session.commit()
		flash("Deleted folder '%s'" % folder.name)
	except ValueError:
		flash('Invalid folder id')
	except NoResultFound:
		flash('No such folder')

	return redirect(url_for('index'))

import api.system
import api.browse


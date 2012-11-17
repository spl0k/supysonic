# coding: utf-8

from flask import Flask, request, session, flash, render_template, redirect, url_for
import string, random, hashlib
import uuid

from web import app
import db

@app.route('/user')
def user_index():
	return render_template('users.html', users = db.User.query.all())

@app.route('/user/add', methods = [ 'GET', 'POST' ])
def add_user():
	if request.method == 'GET':
		return render_template('adduser.html')

	error = False
	(name, passwd, passwd_confirm, mail, admin) = map(request.form.get, [ 'name', 'passwd', 'passwd_confirm', 'mail', 'admin' ])
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
	if admin is None:
		admin = True if db.User.query.filter(db.User.admin == True).count() == 0 else False
	else:
		admin = True
	if error:
		return render_template('adduser.html')

	salt = ''.join(random.choice(string.printable.strip()) for i in xrange(6))
	crypt = hashlib.sha1(salt + passwd).hexdigest()
	user = db.User(name = name, mail = mail, password = crypt, salt = salt, admin = admin)
	db.session.add(user)
	db.session.commit()
	flash("User '%s' successfully added" % name)

	return redirect(url_for('user_index'))

@app.route('/user/del/<id>')
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

	return redirect(url_for('user_index'))

@app.route('/user/login', methods = [ 'GET', 'POST'])
def login():
	return_url = request.args.get('returnUrl') or url_for('index')
	if session.get('userid'):
		flash('Already logged in')
		return redirect(return_url)

	if request.method == 'GET':
		return render_template('login.html')

	user, password = map(request.form.get, [ 'user', 'password' ])
	error = False
	if user in ('', None):
		flash('Missing user name')
		error = True
	if password in ('', None):
		flash('Missing password')
		error = True
	if not error:
		dbuser = db.User.query.filter(db.User.name == user).first()
		if not dbuser:
			flash('Unknown user')
		elif hashlib.sha1(dbuser.salt + password).hexdigest() != dbuser.password:
			flash('Wrong password')
		else:
			session['userid'] = str(dbuser.id)
			session['admin'] = dbuser.admin
			flash('Logged in!')
			return redirect(return_url)

	return render_template('login.html')

@app.route('/user/logout')
def logout():
	session.clear()
	flash('Logged out!')
	return redirect(url_for('login'))


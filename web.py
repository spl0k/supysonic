# coding: utf-8

from flask import Flask, request, session, flash, render_template, redirect, url_for
import db

def create_app():
    app = Flask(__name__)
    app.secret_key = '?9huDM\\H'

    import config
    if(config.get('base', 'accel-redirect')):
        app.use_x_sendfile = True

    if config.get('base', 'debug'):
        app.debug = True
        app.config['SQLALCHEMY_ECHO'] = True

    if config.get('base', 'log_file'):
        import logging
        from logging.handlers import TimedRotatingFileHandler
        handler = TimedRotatingFileHandler(config.get('base', 'log_file'), when = 'midnight', encoding = 'UTF-8')
        handler.setLevel(logging.DEBUG)
        app.logger.addHandler(handler)

    app.config['SQLALCHEMY_DATABASE_URI'] = config.get('base',  'database_uri')

    db.database.init_app(app)

    return app

app = create_app()

with app.app_context():
    db.init_db()

from managers.user import UserManager

@app.before_request
def login_check():
	if request.path.startswith('/rest/'):
		return

	if request.endpoint != 'login':
		should_login = False
		if not session.get('userid'):
			should_login = True
		elif UserManager.get(session.get('userid'))[0] != UserManager.SUCCESS:
			session.clear()
			should_login = True

		if should_login:
			flash('Please login')
			return redirect(url_for('login', returnUrl = request.script_root + request.url[len(request.url_root)-1:]))

@app.template_filter('str')
def to_string(obj):
	return str(obj)

@app.route('/')
def index():
	stats = {
		'artists': db.Artist.query.count(),
		'albums': db.Album.query.count(),
		'tracks': db.Track.query.count()
	}
	return render_template('home.html', stats = stats, admin = UserManager.get(session.get('userid'))[1].admin)

import user
import folder
import playlist

import api.system
import api.browse
import api.user
import api.albums_songs
import api.media
import api.annotation
import api.chat
import api.search
import api.playlists


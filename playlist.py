# coding: utf-8

from flask import request, session, flash, render_template, redirect, url_for
import uuid
from web import app
import db

@app.route('/playlist')
def playlist_index():
	return render_template('playlists.html', mine = db.Playlist.query.filter(db.Playlist.user_id == uuid.UUID(session.get('userid'))),
		others = db.Playlist.query.filter(db.Playlist.user_id != uuid.UUID(session.get('userid'))))

@app.route('/playlist/<uid>')
def playlist_details(uid):
	try:
		uid = uuid.UUID(uid) if type(uid) in (str, unicode) else uid
	except:
		flash('Invalid playlist id')
		return redirect(url_for('playlist_index'))

	playlist = db.Playlist.query.get(uid)
	if not playlist:
		flash('Unknown playlist')
		return redirect(url_for('playlist_index'))

	return render_template('playlist.html', playlist = playlist)

@app.route('/playlist/<uid>', methods = [ 'POST' ])
def playlist_update(uid):
	try:
		uid = uuid.UUID(uid)
	except:
		flash('Invalid playlist id')
		return redirect(url_for('playlist_index'))

	playlist = db.Playlist.query.get(uid)
	if not playlist:
		flash('Unknown playlist')
		return redirect(url_for('playlist_index'))

	if str(playlist.user_id) != session.get('userid'):
		flash("You're not allowed to edit this playlist")
	elif not request.form.get('name'):
		flash('Missing playlist name')
	else:
		playlist.name = request.form.get('name')
		playlist.public = request.form.get('public') in (True, 'True', 1, '1', 'on', 'checked')
		db.session.commit()
		flash('Playlist updated.')

	return playlist_details(uid)

@app.route('/playlist/del/<uid>')
def playlist_delete(uid):
	try:
		uid = uuid.UUID(uid)
	except:
		flash('Invalid playlist id')
		return redirect(url_for('playlist_index'))

	playlist = db.Playlist.query.get(uid)
	if not playlist:
		flash('Unknown playlist')
	elif str(playlist.user_id) != session.get('userid'):
		flash("You're not allowed to delete this playlist")
	else:
		db.session.delete(playlist)
		db.session.commit()
		flash('Playlist deleted')

	return redirect(url_for('playlist_index'))


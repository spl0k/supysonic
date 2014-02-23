# coding: utf-8

from flask import request
from sqlalchemy import or_, func
import uuid
from web import app
from db import Playlist, User, Track, session
from . import get_entity

@app.route('/rest/getPlaylists.view', methods = [ 'GET', 'POST' ])
def list_playlists():
	query = Playlist.query.filter(or_(Playlist.user_id == request.user.id, Playlist.public == True)).order_by(func.lower(Playlist.name))

	username = request.args.get('username')
	if username:
		if not request.user.admin:
			return request.error_formatter(50, 'Restricted to admins')

		query = Playlist.query.join(User).filter(User.name == username).order_by(func.lower(Playlist.name))

	return request.formatter({ 'playlists': { 'playlist': [ p.as_subsonic_playlist(request.user) for p in query ] } })

@app.route('/rest/getPlaylist.view', methods = [ 'GET', 'POST' ])
def show_playlist():
	status, res = get_entity(request, Playlist)
	if not status:
		return res

	info = res.as_subsonic_playlist(request.user)
	info['entry'] = [ t.as_subsonic_child(request.user) for t in res.tracks ]
	return request.formatter({ 'playlist': info })

@app.route('/rest/createPlaylist.view', methods = [ 'GET', 'POST' ])
def create_playlist():
	# Only(?) method where the android client uses form data rather than GET params
	playlist_id, name = map(lambda x: request.args.get(x) or request.form.get(x), [ 'playlistId', 'name' ])
	# songId actually doesn't seem to be required
	songs = request.args.getlist('songId') or request.form.getlist('songId')
	try:
		playlist_id = uuid.UUID(playlist_id) if playlist_id else None
		songs = set(map(uuid.UUID, songs))
	except:
		return request.error_formatter(0, 'Invalid parameter')

	if playlist_id:
		playlist = Playlist.query.get(playlist_id)
		if not playlist:
			return request.error_formatter(70, 'Unknwon playlist')

		if playlist.user_id != request.user.id and not request.user.admin:
			return request.error_formatter(50, "You're not allowed to modify a playlist that isn't yours")

		playlist.tracks = []
		if name:
			playlist.name = name
	elif name:
		playlist = Playlist(user = request.user, name = name)
		session.add(playlist)
	else:
		return request.error_formatter(10, 'Missing playlist id or name')

	for sid in songs:
		track = Track.query.get(sid)
		if not track:
			return request.error_formatter(70, 'Unknown song')

		playlist.tracks.append(track)

	session.commit()
	return request.formatter({})

@app.route('/rest/deletePlaylist.view', methods = [ 'GET', 'POST' ])
def delete_playlist():
	status, res = get_entity(request, Playlist)
	if not status:
		return res

	if res.user_id != request.user.id and not request.user.admin:
		return request.error_formatter(50, "You're not allowed to delete a playlist that isn't yours")

	session.delete(res)
	session.commit()
	return request.formatter({})

@app.route('/rest/updatePlaylist.view', methods = [ 'GET', 'POST' ])
def update_playlist():
	status, res = get_entity(request, Playlist, 'playlistId')
	if not status:
		return res

	if res.user_id != request.user.id and not request.user.admin:
		return request.error_formatter(50, "You're not allowed to delete a playlist that isn't yours")

	playlist = res
	name, comment, public = map(request.args.get, [ 'name', 'comment', 'public' ])
	to_add, to_remove = map(request.args.getlist, [ 'songIdToAdd', 'songIndexToRemove' ])
	try:
		to_add = set(map(uuid.UUID, to_add))
		to_remove = sorted(set(map(int, to_remove)))
	except:
		return request.error_formatter(0, 'Invalid parameter')

	if name:
		playlist.name = name
	if comment:
		playlist.comment = comment
	if public:
		playlist.public = public in (True, 'True', 'true', 1, '1')

	for sid in to_add:
		track = Track.query.get(sid)
		if not track:
			return request.error_formatter(70, 'Unknown song')
		if track not in playlist.tracks:
			playlist.tracks.append(track)

	offset = 0
	for idx in to_remove:
		idx = idx - offset
		if idx < 0 or idx >= len(playlist.tracks):
			return request.error_formatter(0, 'Index out of range')
		playlist.tracks.pop(idx)
		offset += 1

	session.commit()
	return request.formatter({})


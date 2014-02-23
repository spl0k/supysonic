# coding: utf-8

from flask import request
from web import app
from db import Folder, Artist, Album, Track
from api import get_entity
import uuid, time, string

@app.route('/rest/getMusicFolders.view', methods = [ 'GET', 'POST' ])
def list_folders():
	return request.formatter({
		'musicFolders': {
			'musicFolder': [ {
				'id': str(f.id),
				'name': f.name
			} for f in Folder.query.filter(Folder.root == True).order_by(Folder.name).all() ]
		}
	})

@app.route('/rest/getIndexes.view', methods = [ 'GET', 'POST' ])
def list_indexes():
	musicFolderId = request.args.get('musicFolderId')
	ifModifiedSince = request.args.get('ifModifiedSince')
	if ifModifiedSince:
		try:
			ifModifiedSince = int(ifModifiedSince) / 1000
		except:
			return request.error_formatter(0, 'Invalid timestamp')

	if musicFolderId is None:
		folder = Folder.query.filter(Folder.root == True).all()
	else:
		try:
			mfid = uuid.UUID(musicFolderId)
		except:
			return request.error_formatter(0, 'Invalid id')

		folder = Folder.query.get(mfid)

	if not folder or (type(folder) is not list and not folder.root):
		return request.error_formatter(70, 'Folder not found')

	last_modif = max(map(lambda f: f.last_scan, folder)) if type(folder) is list else folder.last_scan

	if (not ifModifiedSince is None) and last_modif < ifModifiedSince:
		return request.formatter({ 'indexes': { 'lastModified': last_modif * 1000 } })

	# The XSD lies, we don't return artists but a directory structure
	if type(folder) is list:
		artists = []
		childs = []
		for f in folder:
			artists += f.children
			childs += f.tracks
	else:
		artists = folder.children
		childs = folder.tracks

	indexes = {}
	for artist in artists:
		index = artist.name[0].upper()
		if index in map(str, xrange(10)):
			index = '#'
		elif index not in string.letters:
			index = '?'

		if index not in indexes:
			indexes[index] = []

		indexes[index].append(artist)

	return request.formatter({
		'indexes': {
			'lastModified': last_modif * 1000,
			'index': [ {
				'name': k,
				'artist': [ {
					'id': str(a.id),
					'name': a.name
				} for a in sorted(v, key = lambda a: a.name.lower()) ]
			} for k, v in sorted(indexes.iteritems()) ],
			'child': [ c.as_subsonic_child(request.user) for c in sorted(childs, key = lambda t: t.sort_key()) ]
		}
	})

@app.route('/rest/getMusicDirectory.view', methods = [ 'GET', 'POST' ])
def show_directory():
	status, res = get_entity(request, Folder)
	if not status:
		return res

	directory = {
		'id': str(res.id),
		'name': res.name,
		'child': [ f.as_subsonic_child(request.user) for f in sorted(res.children, key = lambda c: c.name.lower()) ] + [ t.as_subsonic_child(request.user) for t in sorted(res.tracks, key = lambda t: t.sort_key()) ]
	}
	if not res.root:
		directory['parent'] = str(res.parent_id)

	return request.formatter({ 'directory': directory })

@app.route('/rest/getArtists.view', methods = [ 'GET', 'POST' ])
def list_artists():
	# According to the API page, there are no parameters?
	indexes = {}
	for artist in Artist.query.all():
		index = artist.name[0].upper() if artist.name else '?'
		if index in map(str, xrange(10)):
			index = '#'
		elif index not in string.letters:
			index = '?'

		if index not in indexes:
			indexes[index] = []

		indexes[index].append(artist)

	return request.formatter({
		'artists': {
			'index': [ {
				'name': k,
				'artist': [ a.as_subsonic_artist(request.user) for a in sorted(v, key = lambda a: a.name.lower()) ]
			} for k, v in sorted(indexes.iteritems()) ]
		}
	})

@app.route('/rest/getArtist.view', methods = [ 'GET', 'POST' ])
def artist_info():
	status, res = get_entity(request, Artist)
	if not status:
		return res

	info = res.as_subsonic_artist(request.user)
	info['album'] = [ a.as_subsonic_album(request.user) for a in sorted(res.albums, key = lambda a: a.sort_key()) ]

	return request.formatter({ 'artist': info })

@app.route('/rest/getAlbum.view', methods = [ 'GET', 'POST' ])
def album_info():
	status, res = get_entity(request, Album)
	if not status:
		return res

	info = res.as_subsonic_album(request.user)
	info['song'] = [ t.as_subsonic_child(request.user) for t in sorted(res.tracks, key = lambda t: t.sort_key()) ]

	return request.formatter({ 'album': info })

@app.route('/rest/getSong.view', methods = [ 'GET', 'POST' ])
def track_info():
	status, res = get_entity(request, Track)
	if not status:
		return res

	return request.formatter({ 'song': res.as_subsonic_child(request.user) })

@app.route('/rest/getVideos.view', methods = [ 'GET', 'POST' ])
def list_videos():
	return request.error_formatter(0, 'Video streaming not supported')


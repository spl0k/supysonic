# coding: utf-8

from flask import request
from web import app
from db import Folder, Artist, Album, Track, func, session
from api import get_entity
import uuid, time, string
import os.path

@app.route('/rest/getMusicFolders.view', methods = [ 'GET', 'POST' ])
def list_folders():
	return request.formatter({
		'musicFolders': {
			'musicFolder': [ {
				'id': str(f.id),
				'name': f.name
			} for f in Folder.query.filter(Folder.root == True).order_by(Folder.path).all() ]
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
			artists += f.get_children()
			childs += f.tracks
	else:
		artists = folder.get_children()
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

	res.tracks = [t for t in res.tracks if os.path.isfile(t.path)]

	directory = {
		'id': str(res.id),
		'name': res.name,
		'child': [ f.as_subsonic_child(request.user) for f in res.get_children() ] + [ t.as_subsonic_child(request.user) for t in sorted(res.tracks, key = lambda t: t.sort_key()) ]
	}
	if not res.root:
		parent = Folder.query.with_entities(Folder.id) \
			.filter(Folder.path.like(res.path[:len(res.path)-len(res.name)-1])) \
			.order_by(func.length(Folder.path).desc()).first()
		if parent:
			directory['parent'] = str(parent.id)

	return request.formatter({ 'directory': directory })

@app.route('/rest/getArtists.view', methods = [ 'GET', 'POST' ])
def list_artists():
	# According to the API page, there are no parameters?
	indexes = {}

        # Optimized query instead of using backrefs, is there a way to speed up the backref?
	c = session.query(Album.artist_id, func.count(Album.artist_id).label('c')).group_by(Album.artist_id).subquery(name='c')
	for artist in session.query(Artist.name, Artist.id, c.c.c.label('albums')).join(c).order_by(Artist.name).all():

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
				'artist': [ {
				    'id': str(a.id),
				    'name': a.name.strip(),
				    'albumCount': a.albums
				} for a in v ]
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


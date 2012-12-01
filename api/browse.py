# coding: utf-8

from flask import request
from web import app
from db import Folder, Artist, Album, Track
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
			ifModifiedSince = int(ifModifiedSince)
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
	last_modif_ts = int(time.mktime(last_modif.timetuple()))

	if (not ifModifiedSince is None) and last_modif_ts < ifModifiedSince:
		return request.formatter({ 'indexes': { 'lastModified': last_modif_ts } })

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
			'lastModified': last_modif_ts,
			'index': [ {
				'name': k,
				'artist': [ {
					'id': str(a.id),
					'name': a.name
				} for a in sorted(v, key = lambda a: a.name.lower()) ]
			} for k, v in sorted(indexes.iteritems()) ],
			'child': [ c.as_subsonic_child() for c in sorted(childs, key = lambda t: t.sort_key()) ]
		}
	})

@app.route('/rest/getMusicDirectory.view', methods = [ 'GET', 'POST' ])
def show_directory():
	did = request.args.get('id')
	if not did:
		return request.error_formatter(10, 'Missing directory id')
	try:
		fid = uuid.UUID(did)
	except:
		return request.error_formatter(0, 'Invalid directory id')

	folder = Folder.query.get(fid)
	if not folder:
		return request.error_formatter(70, 'Directory not found')

	directory = {
		'id': str(folder.id),
		'name': folder.name,
		'child': [ f.as_subsonic_child() for f in sorted(folder.children, key = lambda c: c.name) ] + [ t.as_subsonic_child() for t in sorted(folder.tracks, key = lambda t: t.sort_key()) ]
	}
	if not folder.root:
		directory['parent'] = str(folder.parent_id)

	return request.formatter({ 'directory': directory })

@app.route('/rest/getArtists.view', methods = [ 'GET', 'POST' ])
def list_artists():
	# According to the API page, there are no parameter?
	indexes = {}
	for artist in Artist.query.all():
		index = artist.name[0].upper()
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
				'artist': [ a.as_subsonic_artist() for a in sorted(v, key = lambda a: a.name.lower()) ]
			} for k, v in sorted(indexes.iteritems()) ]
		}
	})

@app.route('/rest/getArtist.view', methods = [ 'GET', 'POST' ])
def artist_info():
	id = request.args.get('id')
	if not id:
		return request.error_formatter(10, 'Missing artist id')

	try:
		aid = uuid.UUID(id)
	except:
		return request.error_formatter(0, 'Invalid artist id')

	artist = Artist.query.get(aid)
	if not artist:
		return request.error_formatter(70, 'Artist not found'), 404

	info = artist.as_subsonic_artist()
	info['album'] = [ a.as_subsonic_album() for a in sorted(artist.albums, key = lambda a: a.sort_key()) ]

	return request.formatter({ 'artist': info })

@app.route('/rest/getAlbum.view', methods = [ 'GET', 'POST' ])
def album_info():
	id = request.args.get('id')
	if not id:
		return request.error_formatter(10, 'Missing album id')

	try:
		aid = uuid.UUID(id)
	except:
		return request.error_formatter(0, 'Invalid album id')

	album = Album.query.get(aid)
	if not album:
		return request.error_formatter(70, 'Album not found'), 404

	info = album.as_subsonic_album()
	info['song'] = [ t.as_subsonic_child() for t in sorted(album.tracks, key = lambda t: t.sort_key()) ]

	return request.formatter({ 'artist': info })

@app.route('/rest/getSong.view', methods = [ 'GET', 'POST' ])
def track_info():
	id = request.args.get('id')
	if not id:
		return request.error_formatter(10, 'Missing media id')

	try:
		tid = uuid.UUID(id)
	except:
		return request.error_formatter(0, 'Invalid media id')

	track = Track.query.get(tid)
	if not track:
		return request.error_formatter(70, 'Media not found'), 404

	return request.formatter({ 'song': track.as_subsonic_child() })

@app.route('/rest/getVideos.view', methods = [ 'GET', 'POST' ])
def list_videos():
	return request.error_formatter(0, 'Video streaming not supported')


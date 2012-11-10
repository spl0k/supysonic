# coding: utf-8

from flask import request
from web import app
from db import Folder, Artist, Album, Track
import uuid, time, string

@app.route('/rest/getMusicFolders.view')
def list_folders():
	return request.formatter({
		'musicFolders': {
			'musicFolder': [ {
				'id': str(f.id),
				'name': f.name
			} for f in Folder.query.filter(Folder.root == True).order_by(Folder.name).all() ]
		}
	})

@app.route('/rest/getIndexes.view')
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

	if not folder and not folder.root:
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
			'child': [ c.as_subsonic_child() for c in sorted(childs, key = lambda t: t.album.artist.name + t.album.name + str(t.disc) + str(t.number) + t.title ) ]
		}
	})


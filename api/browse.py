# coding: utf-8

from flask import request
from web import app
from db import MusicFolder, Artist, Album, Track
import uuid, time, string

@app.route('/rest/getMusicFolders.view')
def list_folders():
	return request.formatter({
		'musicFolders': {
			'musicFolder': [ {
				'id': str(f.id),
				'name': f.name
			} for f in MusicFolder.query.order_by(MusicFolder.name).all() ]
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
			return request.formatter({
				'error': {
					'code': 0,
					'message': 'Invalid timestamp'
				}
			}, error = True)

	if musicFolderId is None:
		folder = MusicFolder.query.all()
	else:
		try:
			mfid = uuid.UUID(musicFolderId)
		except:
			return request.formatter({
				'error': {
					'code': 0,
					'message': 'Invalid id'
				}
			}, error = True)

		folder = MusicFolder.query.get(mfid)

	if not folder:
		return request.formatter({
			'error': {
				'code': 70,
				'message': 'Folder not found'
			}
		}, error = True)

	last_modif = max(map(lambda f: f.last_scan, folder)) if type(folder) is list else folder.last_scan
	last_modif_ts = int(time.mktime(last_modif.timetuple()))

	if (not ifModifiedSince is None) and last_modif_ts < ifModifiedSince:
		return request.formatter({ 'indexes': { 'lastModified': last_modif_ts } })

	if type(folder) is list:
		artists = Artist.query.all()
	else:
		artists = Artist.query.join(Album, Track).filter(Track.folder_id == mfid)

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
			} for k, v in sorted(indexes.iteritems()) ]
		}
	})


# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from flask import request
from supysonic.web import app, store
from supysonic.db import Folder, Artist, Album, Track
from . import get_entity
import uuid, string

@app.route('/rest/getMusicFolders.view', methods = [ 'GET', 'POST' ])
def list_folders():
	return request.formatter({
		'musicFolders': {
			'musicFolder': [ {
				'id': str(f.id),
				'name': f.name
			} for f in store.find(Folder, Folder.root == True).order_by(Folder.name) ]
		}
	})

@app.route('/rest/getIndexes.view', methods = [ 'GET', 'POST' ])
def list_indexes():
	musicFolderId = request.values.get('musicFolderId')
	ifModifiedSince = request.values.get('ifModifiedSince')
	if ifModifiedSince:
		try:
			ifModifiedSince = int(ifModifiedSince) / 1000
		except:
			return request.error_formatter(0, 'Invalid timestamp')

	if musicFolderId is None:
		folder = store.find(Folder, Folder.root == True)
	else:
		try:
			mfid = uuid.UUID(musicFolderId)
		except:
			return request.error_formatter(0, 'Invalid id')

		folder = store.get(Folder, mfid)

	if not folder or (type(folder) is Folder and not folder.root):
		return request.error_formatter(70, 'Folder not found')

	last_modif = max(map(lambda f: f.last_scan, folder)) if type(folder) is not Folder else folder.last_scan

	if (not ifModifiedSince is None) and last_modif < ifModifiedSince:
		return request.formatter({ 'indexes': { 'lastModified': last_modif * 1000 } })

	# The XSD lies, we don't return artists but a directory structure
	if type(folder) is not Folder:
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
	for artist in store.find(Artist):
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
	albums  = set(res.albums)
	albums |= { t.album for t in res.tracks }
	info['album'] = [ a.as_subsonic_album(request.user) for a in sorted(albums, key = lambda a: a.sort_key()) ]

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


# coding: utf-8

from flask import request
from web import app
from db import Folder, Track, Artist, Album

@app.route('/rest/search.view', methods = [ 'GET', 'POST' ])
def old_search():
	artist, album, title, anyf, count, offset, newer_than = map(request.args.get, [ 'artist', 'album', 'title', 'any', 'count', 'offset', 'newerThan' ])
	try:
		count = int(count) if count else 20
		offset = int(offset) if offset else 0
		newer_than = int(newer_than) if newer_than else 0
	except:
		return request.error_formatter(0, 'Invalid parameter')

	if artist:
		query = Folder.query.filter(~ Folder.tracks.any(), Folder.name.contains(artist))
	elif album:
		query = Folder.query.filter(Folder.tracks.any(), Folder.name.contains(album))
	elif title:
		query = Track.query.filter(Track.title.contains(title))
	elif anyf:
		folders = Folder.query.filter(Folder.name.contains(anyf))
		tracks = Track.query.filter(Track.title.contains(anyf))
		res = folders.slice(offset, offset + count).all()
		if offset + count > folders.count():
			toff = max(0, offset - folders.count())
			tend = offset + count - folders.count()
			res += tracks.slice(toff, tend).all()

		return request.formatter({ 'searchResult': {
			'totalHits': folders.count() + tracks.count(),
			'offset': offset,
			'match': [ r.as_subsonic_child(request.user) for r in res ]
		}})
	else:
		return request.error_formatter(10, 'Missing search parameter')

	return request.formatter({ 'searchResult': {
		'totalHits': query.count(),
		'offset': offset,
		'match': [ r.as_subsonic_child(request.user) for r in query.slice(offset, offset + count) ]
	}})

@app.route('/rest/search2.view', methods = [ 'GET', 'POST' ])
def new_search():
	query, artist_count, artist_offset, album_count, album_offset, song_count, song_offset = map(
		request.args.get, [ 'query', 'artistCount', 'artistOffset', 'albumCount', 'albumOffset', 'songCount', 'songOffset' ])

	try:
		artist_count = int(artist_count) if artist_count else 20
		artist_offset = int(artist_offset) if artist_offset else 0
		album_count = int(album_count) if album_count else 20
		album_offset = int(album_offset) if album_offset else 0
		song_count = int(song_count) if song_count else 20
		song_offset = int(song_offset) if song_offset else 0
	except:
		return request.error_formatter(0, 'Invalid parameter')

	if not query:
		return request.error_formatter(10, 'Missing query parameter')

	artist_query = Folder.query.filter(~ Folder.tracks.any(), Folder.name.contains(query)).slice(artist_offset, artist_offset + artist_count)
	album_query = Folder.query.filter(Folder.tracks.any(), Folder.name.contains(query)).slice(album_offset, album_offset + album_count)
	song_query = Track.query.filter(Track.title.contains(query)).slice(song_offset, song_offset + song_count)

	return request.formatter({ 'searchResult2': {
		'artist': [ { 'id': str(a.id), 'name': a.name } for a in artist_query ],
		'album': [ f.as_subsonic_child(request.user) for f in album_query ],
		'song': [ t.as_subsonic_child(request.user) for t in song_query ]
	}})

@app.route('/rest/search3.view', methods = [ 'GET', 'POST' ])
def search_id3():
	query, artist_count, artist_offset, album_count, album_offset, song_count, song_offset = map(
		request.args.get, [ 'query', 'artistCount', 'artistOffset', 'albumCount', 'albumOffset', 'songCount', 'songOffset' ])

	try:
		artist_count = int(artist_count) if artist_count else 20
		artist_offset = int(artist_offset) if artist_offset else 0
		album_count = int(album_count) if album_count else 20
		album_offset = int(album_offset) if album_offset else 0
		song_count = int(song_count) if song_count else 20
		song_offset = int(song_offset) if song_offset else 0
	except:
		return request.error_formatter(0, 'Invalid parameter')

	if not query:
		return request.error_formatter(10, 'Missing query parameter')

	artist_query = Artist.query.filter(Artist.name.contains(query)).slice(artist_offset, artist_offset + artist_count)
	album_query = Album.query.filter(Album.name.contains(query)).slice(album_offset, album_offset + album_count)
	song_query = Track.query.filter(Track.title.contains(query)).slice(song_offset, song_offset + song_count)

	return request.formatter({ 'searchResult2': {
		'artist': [ a.as_subsonic_artist(request.user) for a in artist_query ],
		'album': [ a.as_subsonic_album(request.user) for a in album_query ],
		'song': [ t.as_subsonic_child(request.user) for t in song_query ]
	}})


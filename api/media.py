# coding: utf-8

from flask import request, send_file
import os.path
from PIL import Image
from time import time as now

import config
from web import app
from db import Track, Folder, User
from api import get_entity
from lastfm import LastFm

@app.route('/rest/stream.view', methods = [ 'GET', 'POST' ])
def stream_media():
	status, res = get_entity(request, Track)
	if not status:
		return res

	maxBitRate, format, timeOffset, size, estimateContentLength = map(request.args.get, [ 'maxBitRate', 'format', 'timeOffset', 'size', 'estimateContentLength' ])

	if maxBitRate:
		try:
			maxBitRate = int(maxBitRate)
		except:
			return request.error_formatter(0, 'Invalid bitrate value')

		if res.bitrate > maxBitRate:
			# TODO transcode
			pass

	if format != 'mp3':
		# TODO transcode
		pass

	if estimateContentLength == 'true':
		return send_file(res.path), 200, { 'Content-Length': os.path.getsize(res.path) }

	return send_file(res.path)

@app.route('/rest/getCoverArt.view', methods = [ 'GET', 'POST' ])
def cover_art():
	status, res = get_entity(request, Folder)
	if not status:
		return res

	if not res.has_cover_art or not os.path.isfile(os.path.join(res.path, 'cover.jpg')):
		return request.error_formatter(70, 'Cover art not found')

	size = request.args.get('size')
	if size:
		try:
			size = int(size)
		except:
			return request.error_formatter(0, 'Invalid size value')
	else:
		return send_file(os.path.join(res.path, 'cover.jpg'))

	im = Image.open(os.path.join(res.path, 'cover.jpg'))
	if size > im.size[0] and size > im.size[1]:
		return send_file(os.path.join(res.path, 'cover.jpg'))

	size_path = os.path.join(config.get('CACHE_DIR'), str(size))
	path = os.path.join(size_path, str(res.id))
	if os.path.exists(path):
		return send_file(path)
	if not os.path.exists(size_path):
		os.makedirs(size_path)

	im.thumbnail([size, size], Image.ANTIALIAS)
	im.save(path, 'JPEG')
	return send_file(path)

@app.route('/rest/scrobble.view', methods = [ 'GET', 'POST' ])
def scrobble():
	status, res = get_entity(request, Track)
	if not status:
		return res

	time, submission, u = map(request.args.get, [ 'time', 'submission', 'u' ])

	if time:
		try:
			time = int(time) / 1000
		except:
			return request.error_formatter(0, 'Invalid time value')
	else:
		time = int(now())

	if u:
		user = User.query.filter(User.name == u).one()
	else:
		user = User.query.filter(User.name == request.authorization.username).one()
	lfm = LastFm(user, app.logger)

	if submission in (None, '', True, 'true', 'True', 1, '1'):
		lfm.scrobble(res, time)
	else:
		lfm.now_playing(res)

	return request.formatter({})


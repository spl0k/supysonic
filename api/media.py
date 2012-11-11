# coding: utf-8

from flask import request, send_file
import Image
from web import app
from db import Track, Folder
import config
import os.path, uuid

@app.route('/rest/stream.view')
def stream_media():
	id, maxBitRate, format, timeOffset, size, estimateContentLength = map(request.args.get, [ 'id', 'maxBitRate', 'format', 'timeOffset', 'size', 'estimateContentLength' ])
	if not id:
		return request.error_formatter(10, 'Missing media id')

	try:
		tid = uuid.UUID(id)
	except:
		return request.error_formatter(0, 'Invalid media id')

	track = Track.query.get(tid)
	if not track:
		return request.error_formatter(70, 'Media not found'), 404

	if maxBitRate:
		try:
			maxBitRate = int(maxBitRate)
		except:
			return request.error_formatter(0, 'Invalid bitrate value')

		if track.bitrate > maxBitRate:
			# TODO transcode
			pass

	if format != 'mp3':
		# TODO transcode
		pass

	if estimateContentLength == 'true':
		return send_file(track.path), 200, { 'Content-Length': os.path.getsize(track.path) }

	return send_file(track.path)

@app.route('/rest/getCoverArt.view')
def cover_art():
	id = request.args.get('id')
	if not id:
		return request.error_formatter(10, 'Missing cover art id')
	try:
		fid = uuid.UUID(id)
	except:
		return request.error_formatter(0, 'Invalid cover art id')
	folder = Folder.query.get(fid)
	if not folder or not folder.has_cover_art or not os.path.isfile(os.path.join(folder.path, 'cover.jpg')):
		return request.error_formatter(70, 'Cover art not found')

	size = request.args.get('size')
	if size:
		try:
			size = int(size)
		except:
			return request.error_formatter(0, 'Invalid size value')
	else:
		return send_file(os.path.join(folder.path, 'cover.jpg'))

	im = Image.open(os.path.join(folder.path, 'cover.jpg'))
	if size > im.size[0] and size > im.size[1]:
		return send_file(os.path.join(folder.path, 'cover.jpg'))

	size_path = os.path.join(config.get('CACHE_DIR'), str(size))
	path = os.path.join(size_path, id)
	if os.path.exists(path):
		return send_file(path)
	if not os.path.exists(size_path):
		os.makedirs(size_path)

	im.thumbnail([size, size], Image.ANTIALIAS)
	im.save(path, 'JPEG')
	return send_file(path)


# coding: utf-8

from flask import request, send_file
from web import app
from db import Track
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


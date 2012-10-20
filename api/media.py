# coding: utf-8

from flask import request, send_file
from web import app
from db import Track
import os.path, uuid

@app.route('/rest/stream.view')
def stream_media():
	id, maxBitRate, format, timeOffset, size, estimateContentLength = map(request.args.get, [ 'id', 'maxBitRate', 'format', 'timeOffset', 'size', 'estimateContentLength' ])
	if not id:
		return request.formatter({
			'error': {
				'code': 10,
				'message': 'Missing media id'
			}
		}, error = True)

	try:
		tid = uuid.UUID(id)
	except:
		return request.formatter({
			'error': {
				'code': 0,
				'Message': 'Invalid media id'
			}
		}, error = True)

	track = Track.query.get(tid)
	if not track:
		return request.formatter({
			'error': {
				'code': 70,
				'message': 'Media not found'
			}
		}, error = True), 404

	if maxBitRate:
		try:
			maxBitRate = int(maxBitRate)
		except:
			return request.formatter({
				'error': {
					'code': 0,
					'message': 'Invalid bitrate value'
				}
			}, error = True)

		if track.bitrate > maxBitRate:
			# TODO transcode
			pass

	if format != 'mp3':
		# TODO transcode
		pass

	if estimateContentLength == 'true':
		return send_file(track.path), 200, { 'Content-Length': os.path.getsize(track.path) }

	return send_file(track.path)


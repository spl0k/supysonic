# coding: utf-8

from flask import request, send_file, Response
import os.path
from PIL import Image
import subprocess
import shlex
import fnmatch
import mimetypes
from mediafile import MediaFile
import mutagen

import config, scanner
from web import app
from db import Track, Folder, User, ClientPrefs, now, session
from api import get_entity

from flask import g

def after_this_request(func):
	if not hasattr(g, 'call_after_request'):
		g.call_after_request = []
	g.call_after_request.append(func)
	return func

@app.after_request
def per_request_callbacks(response):
	for func in getattr(g, 'call_after_request', ()):
		response = func(response)
	return response

def prepare_transcoding_cmdline(base_cmdline, input_file, input_format, output_format, output_bitrate):
	if not base_cmdline:
		return None

	return base_cmdline.replace('%srcpath', '"'+input_file+'"').replace('%srcfmt', input_format).replace('%outfmt', output_format).replace('%outrate', str(output_bitrate))


@app.route('/rest/stream.view', methods = [ 'GET', 'POST' ])
def stream_media():

	@after_this_request
	def add_header(response):
		if 'X-Sendfile' in response.headers:
			xsendfile = response.headers['X-Sendfile'] or ''
			redirect = config.get('base', 'accel-redirect')
			if redirect and xsendfile:
				response.headers['X-Accel-Charset'] = 'utf-8'
				response.headers['X-Accel-Redirect'] =  redirect + xsendfile.encode('UTF8')
				app.logger.debug('X-Accel-Redirect: ' + redirect + xsendfile)
		return response

	def transcode(process):
		try:
			for chunk in iter(process.stdout.readline, ''):
				yield chunk
			process.wait()
		except:
			app.logger.debug('transcoding timeout, killing process')
			process.terminate()
			process.wait()

	status, res = get_entity(request, Track)

	if not status:
		return res

	maxBitRate, format, timeOffset, size, estimateContentLength, client = map(request.args.get, [ 'maxBitRate', 'format', 'timeOffset', 'size', 'estimateContentLength', 'c' ])
	if format:
		format = format.lower()

	do_transcoding = False
	src_suffix = res.suffix()
	dst_suffix = src_suffix
	dst_bitrate = res.bitrate
	dst_mimetype = mimetypes.guess_type('a.' + src_suffix)

	if maxBitRate:
		try:
			maxBitRate = int(maxBitRate)
		except:
			return request.error_formatter(0, 'Invalid bitrate value')

		if dst_bitrate > maxBitRate and maxBitRate != 0:
			do_transcoding = True
			dst_bitrate = maxBitRate

	if format and format != 'raw' and format != src_suffix:
		do_transcoding = True
		dst_suffix = format
		dst_mimetype = mimetypes.guess_type(dst_suffix)

	if client:
		prefs = ClientPrefs.query.get((request.user.id, client))
		if not prefs:
			prefs = ClientPrefs(user_id = request.user.id, client_name = client)
			session.add(prefs)

		if prefs.format:
			dst_suffix = prefs.format
		if prefs.bitrate and prefs.bitrate < dst_bitrate:
			dst_bitrate = prefs.bitrate


	if not format and src_suffix == 'flac':
		dst_suffix = 'ogg'
		dst_bitrate = 320
		dst_mimetype = 'audio/ogg'
		do_transcoding = True

	duration = mutagen.File(res.path).info.length
	app.logger.debug('Serving file: ' + res.path + '\n\tDuration of file: ' + str(duration))

	if do_transcoding:
		transcoder = config.get('transcoding', 'transcoder_{}_{}'.format(src_suffix, dst_suffix))

		decoder = config.get('transcoding', 'decoder_' + src_suffix) or config.get('transcoding', 'decoder')
		encoder = config.get('transcoding', 'encoder_' + dst_suffix) or config.get('transcoding', 'encoder')

		if not transcoder and (not decoder or not encoder):
			transcoder = config.get('transcoding', 'transcoder')
			if not transcoder:
				return request.error_formatter(0, 'No way to transcode from {} to {}'.format(src_suffix, dst_suffix))

		transcoder, decoder, encoder = map(lambda x: prepare_transcoding_cmdline(x, res.path, src_suffix, dst_suffix, dst_bitrate), [ transcoder, decoder, encoder ])

		decoder = map(lambda s: s.decode('UTF8'), shlex.split(decoder.encode('utf8')))
		encoder = map(lambda s: s.decode('UTF8'), shlex.split(encoder.encode('utf8')))
		transcoder = map(lambda s: s.decode('UTF8'), shlex.split(transcoder.encode('utf8')))

		app.logger.debug(str( decoder ) + '\n' + str( encoder ) + '\n' + str(transcoder))

		if '|' in transcoder:
			pipe_index = transcoder.index('|')
			decoder = transcoder[:pipe_index]
			encoder = transcoder[pipe_index+1:]
			transcoder = None

		app.logger.debug('decoder' + str(decoder) + '\nencoder' + str(encoder))

		try:
			if transcoder:
				app.logger.warn('transcoder: '+str(transcoder))
				proc = subprocess.Popen(transcoder, stdout = subprocess.PIPE, shell=False)
			else:
				dec_proc = subprocess.Popen(decoder, stdout = subprocess.PIPE, shell=False)
				proc = subprocess.Popen(encoder, stdin = dec_proc.stdout, stdout = subprocess.PIPE, shell=False)

			response = Response(transcode(proc), 200, {'Content-Type': dst_mimetype, 'X-Content-Duration': str(duration)})
		except:
			return request.error_formatter(0, 'Error while running the transcoding process')

	else:
		app.logger.warn('no transcode')
		response = send_file(res.path)
		response.headers['Content-Type'] = dst_mimetype
		response.headers['Accept-Ranges'] = 'bytes'
		response.headers['X-Content-Duration'] = str(duration)

	res.play_count = res.play_count + 1
	res.last_play = now()
	request.user.last_play = res
	request.user.last_play_date = now()
	session.commit()

	return response

@app.route('/rest/download.view', methods = [ 'GET', 'POST' ])
def download_media():
	status, res = get_entity(request, Track)
	if not status:
		return res

	return send_file(res.path)

@app.route('/rest/getCoverArt.view', methods = [ 'GET', 'POST' ])
def cover_art():

        # Speed up the file transfer
	@after_this_request
	def add_header(response):
		response.headers['Content-Type'] = 'image/jpeg'
		if 'X-Sendfile' in response.headers:
			redirect = response.headers['X-Sendfile'] or ''
			xsendfile = config.get('base', 'accel-redirect')
			if redirect and xsendfile:
				response.headers['X-Accel-Redirect'] =  xsendfile + redirect
				app.logger.debug('X-Accel-Redirect: ' + xsendfile + redirect)
		return response

        # retrieve folder from database
	status, res = get_entity(request, Folder)

	if not status:
		return res

        # Check the folder id given for jpgs
	app.logger.debug('Cover Art Check: ' + res.path + '/*.jp*g')

	coverfile = os.listdir(res.path)
	coverfile = fnmatch.filter(coverfile, '*.jp*g')
	app.logger.debug('Found Images: ' + str(coverfile))

        # when there is not a jpeg in the folder check files for embedded art
	if not coverfile:
		app.logger.debug('No Art Found in Folder, Checking Files!')

		for tr in res.tracks:
			app.logger.debug('Checking ' + tr.path + ' For Artwork')
			try:
				mf = MediaFile(tr.path)
				coverfile = getattr(mf, 'art')
				if coverfile is not None:
					return coverfile
			except:
				app.logger.debug('Problem reading embedded art')

		tr.folder.has_cover_art = False
		session.commit()
		return request.error_formatter(70, 'Cover art not found'), 404

        # pick the first image found
        # TODO: prefer cover
	coverfile = coverfile[0]

	size = request.args.get('size')
	if size:
		try:
			size = int(size)
		except:
			return request.error_formatter(0, 'Invalid size value'), 500
	else:
		app.logger.debug('Serving cover art: ' + res.path + coverfile)
		return send_file(os.path.join(res.path, coverfile))

	im = Image.open(os.path.join(res.path, coverfile))
	if size > im.size[0] and size > im.size[1]:
		app.logger.debug('Serving cover art: ' + res.path + coverfile)
		return send_file(os.path.join(res.path, coverfile))

	size_path = os.path.join(config.get('base', 'cache_dir'), str(size))
	path = os.path.join(size_path, str(res.id))
	if os.path.exists(path):
		app.logger.debug('Serving cover art: ' + path)
		return send_file(path)
	if not os.path.exists(size_path):
		os.makedirs(size_path)

	im.thumbnail([size, size], Image.ANTIALIAS)
	im.save(path, 'JPEG')

	app.logger.debug('Serving cover art: ' + path)
	return send_file(path)


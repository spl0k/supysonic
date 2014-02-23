# coding: utf-8

from flask import request, send_file, Response
import requests
import os.path
from PIL import Image
import subprocess
import codecs
from xml.etree import ElementTree

import config, scanner
from web import app
from db import Track, Album, Artist, Folder, User, ClientPrefs, now, session
from api import get_entity

from sqlalchemy import func

def prepare_transcoding_cmdline(base_cmdline, input_file, input_format, output_format, output_bitrate):
	if not base_cmdline:
		return None
	ret = base_cmdline.split()
	for i in xrange(len(ret)):
		ret[i] = ret[i].replace('%srcpath', input_file).replace('%srcfmt', input_format).replace('%outfmt', output_format).replace('%outrate', str(output_bitrate))
	return ret

@app.route('/rest/stream.view', methods = [ 'GET', 'POST' ])
def stream_media():
	status, res = get_entity(request, Track)
	if not status:
		return res

	maxBitRate, format, timeOffset, size, estimateContentLength, client = map(request.args.get, [ 'maxBitRate', 'format', 'timeOffset', 'size', 'estimateContentLength', 'c' ])
	if format:
		format = format.lower()

	src_suffix = res.suffix()
	dst_suffix = res.suffix()
	dst_bitrate = res.bitrate
	dst_mimetype = res.content_type

	if client:
		prefs = ClientPrefs.query.get((request.user.id, client))
		if not prefs:
			prefs = ClientPrefs(user_id = request.user.id, client_name = client)
			session.add(prefs)

		if prefs.format:
			dst_suffix = prefs.format
		if prefs.bitrate and prefs.bitrate < dst_bitrate:
			dst_bitrate = prefs.bitrate

	if maxBitRate:
		try:
			maxBitRate = int(maxBitRate)
		except:
			return request.error_formatter(0, 'Invalid bitrate value')

		if dst_bitrate > maxBitRate and maxBitRate != 0:
			dst_bitrate = maxBitRate

	if format and format != 'raw' and format != src_suffix:
		dst_suffix = format
		dst_mimetype = scanner.get_mime(dst_suffix)

	if format != 'raw' and (dst_suffix != src_suffix or dst_bitrate != res.bitrate):
		transcoder = config.get('transcoding', 'transcoder_{}_{}'.format(src_suffix, dst_suffix))
		decoder = config.get('transcoding', 'decoder_' + src_suffix) or config.get('transcoding', 'decoder')
		encoder = config.get('transcoding', 'encoder_' + dst_suffix) or config.get('transcoding', 'encoder')
		if not transcoder and (not decoder or not encoder):
			transcoder = config.get('transcoding', 'transcoder')
			if not transcoder:
				return request.error_formatter(0, 'No way to transcode from {} to {}'.format(src_suffix, dst_suffix))

		transcoder, decoder, encoder = map(lambda x: prepare_transcoding_cmdline(x, res.path, src_suffix, dst_suffix, dst_bitrate), [ transcoder, decoder, encoder ])
		try:
			if transcoder:
				proc = subprocess.Popen(transcoder, stdout = subprocess.PIPE)
			else:
				dec_proc = subprocess.Popen(decoder, stdout = subprocess.PIPE)
				proc = subprocess.Popen(encoder, stdin = dec_proc.stdout, stdout = subprocess.PIPE)
		except:
			return request.error_formatter(0, 'Error while running the transcoding process')

		def transcode():
			while True:
				data = proc.stdout.read(8192)
				if not data:
					break
				yield data
			proc.terminate()
			proc.wait()

		app.logger.info('Transcoding track {0.id} for user {1.id}. Source: {2} at {0.bitrate}kbps. Dest: {3} at {4}kbps'.format(res, request.user, src_suffix, dst_suffix, dst_bitrate))
		response = Response(transcode(), mimetype = dst_mimetype)
	else:
		response = send_file(res.path, mimetype = dst_mimetype)

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

	size_path = os.path.join(config.get('base', 'cache_dir'), str(size))
	path = os.path.join(size_path, str(res.id))
	if os.path.exists(path):
		return send_file(path)
	if not os.path.exists(size_path):
		os.makedirs(size_path)

	im.thumbnail([size, size], Image.ANTIALIAS)
	im.save(path, 'JPEG')
	return send_file(path)

@app.route('/rest/getLyrics.view', methods = [ 'GET', 'POST' ])
def lyrics():
	artist, title = map(request.args.get, [ 'artist', 'title' ])
	if not artist:
		return request.error_formatter(10, 'Missing artist parameter')
	if not title:
		return request.error_formatter(10, 'Missing title parameter')

	query = Track.query.join(Album, Artist).filter(func.lower(Track.title) == title.lower() and func.lower(Artist.name) == artist.lower())
	for track in query:
		lyrics_path = os.path.splitext(track.path)[0] + '.txt'
		if os.path.exists(lyrics_path):
			app.logger.debug('Found lyrics file: ' + lyrics_path)

			try:
				lyrics = read_file_as_unicode(lyrics_path)
			except UnicodeError:
				# Lyrics file couldn't be decoded. Rather than displaying an error, try with the potential next files or
				# return no lyrics. Log it anyway.
				app.logger.warn('Unsupported encoding for lyrics file ' + lyrics_path)
				continue

			return request.formatter({ 'lyrics': {
				'artist': track.album.artist.name,
				'title': track.title,
				'_value_': lyrics
			} })

	try:
		r = requests.get("http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect",
			params = { 'artist': artist, 'song': title })
		root = ElementTree.fromstring(r.content)

		ns = { 'cl': 'http://api.chartlyrics.com/' }
		return request.formatter({ 'lyrics': {
			'artist': root.find('cl:LyricArtist', namespaces = ns).text,
			'title': root.find('cl:LyricSong', namespaces = ns).text,
			'_value_': root.find('cl:Lyric', namespaces = ns).text
		} })
	except requests.exceptions.RequestException, e:
		app.logger.warn('Error while requesting the ChartLyrics API: ' + str(e))

	return request.formatter({ 'lyrics': {} })

def read_file_as_unicode(path):
	""" Opens a file trying with different encodings and returns the contents as a unicode string """

	encodings = [ 'utf-8', 'latin1' ] # Should be extended to support more encodings

	for enc in encodings:
		try:
			contents = codecs.open(path, 'r', encoding = enc).read()
			app.logger.debug('Read file {} with {} encoding'.format(path, enc))
			# Maybe save the encoding somewhere to prevent going through this loop each time for the same file
			return contents
		except UnicodeError:
			pass

	# Fallback to ASCII
	app.logger.debug('Reading file {} with ascii encoding'.format(path))
	return unicode(open(path, 'r').read())


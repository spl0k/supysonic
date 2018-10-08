# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import codecs
import mimetypes
import mutagen
import os.path
import requests
import shlex
import subprocess
import tempfile

from flask import request, Response, send_file
from flask import current_app
from PIL import Image
from xml.etree import ElementTree

from .. import scanner
from ..db import Track, Album, Artist, Folder, User, ClientPrefs, now
from ..py23 import dict

from . import api, get_entity
from .exceptions import GenericError, MissingParameter, NotFound, ServerError, UnsupportedParameter

def prepare_transcoding_cmdline(base_cmdline, input_file, input_format, output_format, output_bitrate):
    if not base_cmdline:
        return None
    ret = shlex.split(base_cmdline)
    ret = [
        part.replace('%srcpath', input_file).replace('%srcfmt', input_format).replace('%outfmt', output_format).replace('%outrate', str(output_bitrate))
        for part in ret
    ]
    return ret

@api.route('/stream.view', methods = [ 'GET', 'POST' ])
def stream_media():
    res = get_entity(Track)

    if 'timeOffset' in request.values:
        raise UnsupportedParameter('timeOffset')
    if 'size' in request.values:
        raise UnsupportedParameter('size')

    maxBitRate, format, estimateContentLength = map(request.values.get, [ 'maxBitRate', 'format', 'estimateContentLength' ])
    if format:
        format = format.lower()

    src_suffix = res.suffix()
    dst_suffix = res.suffix()
    dst_bitrate = res.bitrate
    dst_mimetype = res.content_type

    prefs = request.client
    if prefs.format:
        dst_suffix = prefs.format
    if prefs.bitrate and prefs.bitrate < dst_bitrate:
        dst_bitrate = prefs.bitrate

    if maxBitRate:
        maxBitRate = int(maxBitRate)

        if dst_bitrate > maxBitRate and maxBitRate != 0:
            dst_bitrate = maxBitRate

    if format and format != 'raw' and format != src_suffix:
        dst_suffix = format
        dst_mimetype = mimetypes.guess_type('dummyname.' + dst_suffix, False)[0] or 'application/octet-stream'

    if format != 'raw' and (dst_suffix != src_suffix or dst_bitrate != res.bitrate):
        config = current_app.config['TRANSCODING']
        transcoder = config.get('transcoder_{}_{}'.format(src_suffix, dst_suffix))
        decoder = config.get('decoder_' + src_suffix) or config.get('decoder')
        encoder = config.get('encoder_' + dst_suffix) or config.get('encoder')
        if not transcoder and (not decoder or not encoder):
            transcoder = config.get('transcoder')
            if not transcoder:
                message = 'No way to transcode from {} to {}'.format(src_suffix, dst_suffix)
                current_app.logger.info(message)
                raise GenericError(message)

        transcoder, decoder, encoder = map(lambda x: prepare_transcoding_cmdline(x, res.path, src_suffix, dst_suffix, dst_bitrate), [ transcoder, decoder, encoder ])
        try:
            if transcoder:
                dec_proc = None
                proc = subprocess.Popen(transcoder, stdout = subprocess.PIPE)
            else:
                dec_proc = subprocess.Popen(decoder, stdout = subprocess.PIPE)
                proc = subprocess.Popen(encoder, stdin = dec_proc.stdout, stdout = subprocess.PIPE)
        except OSError:
            raise ServerError('Error while running the transcoding process')

        def transcode():
            try:
                while True:
                    data = proc.stdout.read(8192)
                    if not data:
                        break
                    yield data
            except: # pragma: nocover
                if dec_proc != None:
                    dec_proc.terminate()
                proc.terminate()

            if dec_proc != None:
                dec_proc.wait()
            proc.wait()

        current_app.logger.info('Transcoding track {0.id} for user {1.id}. Source: {2} at {0.bitrate}kbps. Dest: {3} at {4}kbps'.format(res, request.user, src_suffix, dst_suffix, dst_bitrate))
        response = Response(transcode(), mimetype = dst_mimetype)
        if estimateContentLength == 'true':
            response.headers.add('Content-Length', dst_bitrate * 1000 * res.duration // 8)
    else:
        response = send_file(res.path, mimetype = dst_mimetype, conditional=True)

    res.play_count = res.play_count + 1
    res.last_play = now()
    user = request.user
    user.last_play = res
    user.last_play_date = now()

    return response

@api.route('/download.view', methods = [ 'GET', 'POST' ])
def download_media():
    res = get_entity(Track)
    return send_file(res.path, mimetype = res.content_type, conditional=True)

@api.route('/getCoverArt.view', methods = [ 'GET', 'POST' ])
def cover_art():
    res = get_entity(Folder)
    if not res.cover_art or not os.path.isfile(os.path.join(res.path, res.cover_art)):
        # Check for embeded metadata in songs
        temp_cover = tempfile.NamedTemporaryFile()
        cover_path = temp_cover.name
        for track in res.tracks:
            song = mutagen.File(track.path)
            if type(song) == mutagen.mp3.MP3 and len(song.tags.getall('APIC')) > 0:
                temp_cover.write(song.tags.getall('APIC')[0].data)
                break
        else:
            raise NotFound('Cover art')
    else:
        cover_path = os.path.join(res.path, res.cover_art)
    size = request.values.get('size')
    if size:
        size = int(size)
    else:
        return send_file(cover_path)

    im = Image.open(cover_path)
    if size > im.width and size > im.height:
        return send_file(cover_path)

    size_path = os.path.join(current_app.config['WEBAPP']['cache_dir'], str(size))
    path = os.path.abspath(os.path.join(size_path, str(res.id)))
    if os.path.exists(path):
        return send_file(path, mimetype = 'image/' + im.format.lower())
    if not os.path.exists(size_path):
        os.makedirs(size_path)

    im.thumbnail([size, size], Image.ANTIALIAS)
    im.save(path, im.format)
    return send_file(path, mimetype = 'image/' + im.format.lower())

@api.route('/getLyrics.view', methods = [ 'GET', 'POST' ])
def lyrics():
    artist = request.values['artist']
    title = request.values['title']

    query = Track.select(lambda t: title in t.title and artist in t.artist.name)
    for track in query:
        lyrics_path = os.path.splitext(track.path)[0] + '.txt'
        if os.path.exists(lyrics_path):
            current_app.logger.debug('Found lyrics file: ' + lyrics_path)

            try:
                lyrics = read_file_as_unicode(lyrics_path)
            except UnicodeError:
                # Lyrics file couldn't be decoded. Rather than displaying an error, try with the potential next files or
                # return no lyrics. Log it anyway.
                current_app.logger.warning('Unsupported encoding for lyrics file ' + lyrics_path)
                continue

            return request.formatter('lyrics', dict(
                artist = track.album.artist.name,
                title = track.title,
                _value_ = lyrics
            ))

    try:
        r = requests.get("http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect",
            params = { 'artist': artist, 'song': title })
        root = ElementTree.fromstring(r.content)

        ns = { 'cl': 'http://api.chartlyrics.com/' }
        return request.formatter('lyrics', dict(
            artist = root.find('cl:LyricArtist', namespaces = ns).text,
            title = root.find('cl:LyricSong', namespaces = ns).text,
            _value_ = root.find('cl:Lyric', namespaces = ns).text
        ))
    except requests.exceptions.RequestException as e: # pragma: nocover
        current_app.logger.warning('Error while requesting the ChartLyrics API: ' + str(e))

    return request.formatter('lyrics', dict()) # pragma: nocover

def read_file_as_unicode(path):
    """ Opens a file trying with different encodings and returns the contents as a unicode string """

    encodings = [ 'utf-8', 'latin1' ] # Should be extended to support more encodings

    for enc in encodings:
        try:
            contents = codecs.open(path, 'r', encoding = enc).read()
            current_app.logger.debug('Read file {} with {} encoding'.format(path, enc))
            # Maybe save the encoding somewhere to prevent going through this loop each time for the same file
            return contents
        except UnicodeError:
            pass

    # Fallback to ASCII
    current_app.logger.debug('Reading file {} with ascii encoding'.format(path))
    return unicode(open(path, 'r').read())


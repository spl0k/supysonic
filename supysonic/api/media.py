# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import codecs
import logging
import mimetypes
import os.path
import requests
import shlex
import subprocess
import uuid
import io
import hashlib
import json
import zlib

from flask import request, Response, send_file
from flask import current_app
from PIL import Image
from pony.orm import ObjectNotFound
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED
from zipstream import ZipFile

from .. import scanner
from ..cache import CacheMiss
from ..db import Track, Album, Artist, Folder, User, ClientPrefs, now
from ..py23 import dict

from . import api, get_entity
from .exceptions import GenericError, MissingParameter, NotFound, ServerError, UnsupportedParameter

logger = logging.getLogger(__name__)

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
        # Requires transcoding
        cache = current_app.transcode_cache
        cache_key = "{}-{}.{}".format(res.id, dst_bitrate, dst_suffix)

        try:
            response = send_file(cache.get(cache_key), mimetype=dst_mimetype, conditional=True)
        except CacheMiss:
            config = current_app.config['TRANSCODING']
            transcoder = config.get('transcoder_{}_{}'.format(src_suffix, dst_suffix))
            decoder = config.get('decoder_' + src_suffix) or config.get('decoder')
            encoder = config.get('encoder_' + dst_suffix) or config.get('encoder')
            if not transcoder and (not decoder or not encoder):
                transcoder = config.get('transcoder')
                if not transcoder:
                    message = 'No way to transcode from {} to {}'.format(src_suffix, dst_suffix)
                    logger.info(message)
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
                        dec_proc.kill()
                    proc.kill()
                    raise
                finally:
                    if dec_proc != None:
                        dec_proc.wait()
                    proc.wait()
            resp_content = cache.set_generated(cache_key, transcode)

            logger.info('Transcoding track {0.id} for user {1.id}. Source: {2} at {0.bitrate}kbps. Dest: {3} at {4}kbps'.format(res, request.user, src_suffix, dst_suffix, dst_bitrate))
            response = Response(resp_content, mimetype=dst_mimetype)
            if estimateContentLength == 'true':
                response.headers.add('Content-Length', dst_bitrate * 1000 * res.duration // 8)
    else:
        response = send_file(res.path, mimetype=dst_mimetype, conditional=True)

    res.play_count = res.play_count + 1
    res.last_play = now()
    user = request.user
    user.last_play = res
    user.last_play_date = now()

    return response

@api.route('/download.view', methods = [ 'GET', 'POST' ])
def download_media():
    id = request.values['id']
    uid = uuid.UUID(id)

    try: # Track -> direct download
        rv = Track[uid]
        return send_file(rv.path, mimetype = rv.content_type, conditional=True)
    except ObjectNotFound:
        pass

    try: # Folder -> stream zipped tracks, non recursive
        rv = Folder[uid]
    except ObjectNotFound:
        try: # Album -> stream zipped tracks
            rv = Album[uid]
        except ObjectNotFound:
            raise NotFound('Track, Folder or Album')

    z = ZipFile(compression = ZIP_DEFLATED)
    for track in rv.tracks:
        z.write(track.path, os.path.basename(track.path))
    resp = Response(z, mimetype = 'application/zip')
    resp.headers['Content-Disposition'] = 'attachment; filename={}.zip'.format(rv.name)
    return resp

@api.route('/getCoverArt.view', methods = [ 'GET', 'POST' ])
def cover_art():
    cache = current_app.cache
    eid = request.values['id']
    if Folder.exists(id=eid):
        res = get_entity(Folder)
        if not res.cover_art or not os.path.isfile(os.path.join(res.path, res.cover_art)):
            raise NotFound('Cover art')
        cover_path = os.path.join(res.path, res.cover_art)
    elif Track.exists(id=eid):
        cache_key = "{}-cover".format(eid)
        try:
            cover_path = cache.get(cache_key)
        except CacheMiss:
            res = get_entity(Track)
            art = res.extract_cover_art()
            if not art:
                raise NotFound('Cover art')
            cover_path = cache.set(cache_key, art)
    else:
        raise NotFound('Entity')

    size = request.values.get('size')
    if size:
        size = int(size)
    else:
        return send_file(cover_path)

    im = Image.open(cover_path)
    mimetype = 'image/{}'.format(im.format.lower())
    if size > im.width and size > im.height:
        return send_file(cover_path, mimetype=mimetype)

    cache_key = "{}-cover-{}".format(eid, size)
    try:
        return send_file(cache.get(cache_key), mimetype=mimetype)
    except CacheMiss:
        im.thumbnail([size, size], Image.ANTIALIAS)
        with cache.set_fileobj(cache_key) as fp:
            im.save(fp, im.format)
        return send_file(cache.get(cache_key), mimetype=mimetype)

@api.route('/getLyrics.view', methods = [ 'GET', 'POST' ])
def lyrics():
    artist = request.values['artist']
    title = request.values['title']

    query = Track.select(lambda t: title in t.title and artist in t.artist.name)
    for track in query:
        lyrics_path = os.path.splitext(track.path)[0] + '.txt'
        if os.path.exists(lyrics_path):
            logger.debug('Found lyrics file: ' + lyrics_path)

            try:
                lyrics = read_file_as_unicode(lyrics_path)
            except UnicodeError:
                # Lyrics file couldn't be decoded. Rather than displaying an error, try with the potential next files or
                # return no lyrics. Log it anyway.
                logger.warning('Unsupported encoding for lyrics file ' + lyrics_path)
                continue

            return request.formatter('lyrics', dict(
                artist = track.album.artist.name,
                title = track.title,
                value = lyrics
            ))

    # Create a stable, unique, filesystem-compatible identifier for the artist+title
    unique = hashlib.md5(json.dumps([x.lower() for x in (artist, title)]).encode('utf-8')).hexdigest()
    cache_key = "lyrics-{}".format(unique)

    lyrics = dict()
    try:
        lyrics = json.loads(
            zlib.decompress(
                current_app.cache.get_value(cache_key)
            ).decode('utf-8')
        )
    except (CacheMiss, zlib.error, TypeError, ValueError):
        try:
            r = requests.get("http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect",
                             params={'artist': artist, 'song': title}, timeout=5)
            root = ElementTree.fromstring(r.content)

            ns = {'cl': 'http://api.chartlyrics.com/'}
            lyrics = dict(
                artist = root.find('cl:LyricArtist', namespaces=ns).text,
                title = root.find('cl:LyricSong', namespaces=ns).text,
                value = root.find('cl:Lyric', namespaces=ns).text
            )

            current_app.cache.set(
                cache_key, zlib.compress(json.dumps(lyrics).encode('utf-8'), 9)
            )
        except requests.exceptions.RequestException as e: # pragma: nocover
            logger.warning('Error while requesting the ChartLyrics API: ' + str(e))

    return request.formatter('lyrics', lyrics)

def read_file_as_unicode(path):
    """ Opens a file trying with different encodings and returns the contents as a unicode string """

    encodings = [ 'utf-8', 'latin1' ] # Should be extended to support more encodings

    for enc in encodings:
        try:
            contents = codecs.open(path, 'r', encoding = enc).read()
            logger.debug('Read file {} with {} encoding'.format(path, enc))
            # Maybe save the encoding somewhere to prevent going through this loop each time for the same file
            return contents
        except UnicodeError:
            pass

    # Fallback to ASCII
    logger.debug('Reading file {} with ascii encoding'.format(path))
    return unicode(open(path, 'r').read())

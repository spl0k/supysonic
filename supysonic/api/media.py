# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#               2018-2019 Carey 'pR0Ps' Metcalfe
#
# Distributed under terms of the GNU AGPLv3 license.

import hashlib
import json
import logging
import mediafile
import mimetypes
import os.path
import requests
import shlex
import subprocess
import zlib

from flask import request, Response, send_file
from flask import current_app
from PIL import Image
from xml.etree import ElementTree
from zipstream import ZipStream

from ..cache import CacheMiss
from ..db import Track, Album, Artist, Folder, now
from ..covers import EXTENSIONS

from . import get_entity, get_entity_id, api_routing
from .exceptions import (
    GenericError,
    NotFound,
    ServerError,
    UnsupportedParameter,
)

logger = logging.getLogger(__name__)


def prepare_transcoding_cmdline(
    base_cmdline, res, input_format, output_format, output_bitrate
):
    if not base_cmdline:
        return None
    ret = shlex.split(base_cmdline)
    ret = [
        part.replace("%srcpath", res.path)
        .replace("%srcfmt", input_format)
        .replace("%outfmt", output_format)
        .replace("%outrate", str(output_bitrate))
        .replace("%title", res.title)
        .replace("%album", res.album.name)
        .replace("%artist", res.artist.name)
        .replace("%tracknumber", str(res.number))
        .replace("%totaltracks", str(res.album.tracks.count()))
        .replace("%discnumber", str(res.disc))
        .replace("%genre", res.genre if res.genre else "")
        .replace("%year", str(res.year) if res.year else "")
        for part in ret
    ]
    return ret


@api_routing("/stream")
def stream_media():
    res = get_entity(Track)

    if "timeOffset" in request.values:
        raise UnsupportedParameter("timeOffset")
    if "size" in request.values:
        raise UnsupportedParameter("size")

    maxBitRate, request_format, estimateContentLength = map(
        request.values.get, ("maxBitRate", "format", "estimateContentLength")
    )
    if request_format:
        request_format = request_format.lower()

    src_suffix = res.suffix()
    dst_suffix = res.suffix()
    dst_bitrate = res.bitrate
    dst_mimetype = res.mimetype

    config = current_app.config["TRANSCODING"]
    prefs = request.client

    using_default_format = False
    if request_format:
        dst_suffix = src_suffix if request_format == "raw" else request_format
    elif prefs.format:
        dst_suffix = prefs.format
    else:
        using_default_format = True
        dst_suffix = src_suffix

    if prefs.bitrate and prefs.bitrate < dst_bitrate:
        dst_bitrate = prefs.bitrate

    if maxBitRate:
        maxBitRate = int(maxBitRate)

        if dst_bitrate > maxBitRate and maxBitRate != 0:
            dst_bitrate = maxBitRate
            if using_default_format:
                dst_suffix = config.get("default_transcode_target") or dst_suffix

    # Find new mimetype if we're changing formats
    if dst_suffix != src_suffix:
        dst_mimetype = (
            mimetypes.guess_type("dummyname." + dst_suffix, False)[0]
            or "application/octet-stream"
        )

    if dst_suffix != src_suffix or dst_bitrate != res.bitrate:
        # Requires transcoding
        cache = current_app.transcode_cache
        cache_key = f"{res.id}-{dst_bitrate}.{dst_suffix}"

        try:
            response = send_file(
                cache.get(cache_key), mimetype=dst_mimetype, conditional=True
            )
        except CacheMiss:
            transcoder = config.get(f"transcoder_{src_suffix}_{dst_suffix}")
            decoder = config.get("decoder_" + src_suffix) or config.get("decoder")
            encoder = config.get("encoder_" + dst_suffix) or config.get("encoder")
            if not transcoder and (not decoder or not encoder):
                transcoder = config.get("transcoder")
                if not transcoder:
                    message = "No way to transcode from {} to {}".format(
                        src_suffix, dst_suffix
                    )
                    logger.info(message)
                    raise GenericError(message)

            transcoder, decoder, encoder = (
                prepare_transcoding_cmdline(x, res, src_suffix, dst_suffix, dst_bitrate)
                for x in (transcoder, decoder, encoder)
            )
            try:
                if transcoder:
                    dec_proc = None
                    proc = subprocess.Popen(transcoder, stdout=subprocess.PIPE)
                else:
                    dec_proc = subprocess.Popen(decoder, stdout=subprocess.PIPE)
                    proc = subprocess.Popen(
                        encoder, stdin=dec_proc.stdout, stdout=subprocess.PIPE
                    )
            except OSError:
                raise ServerError("Error while running the transcoding process")

            if estimateContentLength == "true":
                estimate = dst_bitrate * 1000 * res.duration // 8
            else:
                estimate = None

            def transcode():
                while True:
                    data = proc.stdout.read(8192)
                    if not data:
                        break
                    yield data

            def kill_processes():
                if dec_proc is not None:
                    dec_proc.kill()
                proc.kill()

            def handle_transcoding():
                try:
                    sent = 0
                    for data in transcode():
                        sent += len(data)
                        yield data
                except (Exception, SystemExit, KeyboardInterrupt):
                    # Make sure child processes are always killed
                    kill_processes()
                    raise
                except GeneratorExit:
                    # Try to transcode/send more data if we're close to the end.
                    # The calling code have to support this as yielding more data
                    # after a GeneratorExit would normally raise a RuntimeError.
                    # Hopefully this generator is only used by the cache which
                    # handles this.
                    if estimate and sent >= estimate * 0.95:
                        yield from transcode()
                    else:
                        kill_processes()
                        raise
                finally:
                    if dec_proc is not None:
                        dec_proc.stdout.close()
                        dec_proc.wait()
                    proc.stdout.close()
                    proc.wait()

            resp_content = cache.set_generated(cache_key, handle_transcoding)

            logger.info(
                "Transcoding track {0.id} for user {1.id}. Source: {2} at {0.bitrate}kbps. Dest: {3} at {4}kbps".format(
                    res, request.user, src_suffix, dst_suffix, dst_bitrate
                )
            )
            response = Response(resp_content, mimetype=dst_mimetype)
            if estimate is not None:
                response.headers.add("Content-Length", estimate)
    else:
        response = send_file(res.path, mimetype=dst_mimetype, conditional=True)

    res.play_count = res.play_count + 1
    res.last_play = now()
    res.save()

    user = request.user
    user.last_play = res
    user.last_play_date = now()
    user.save()

    return response


@api_routing("/download")
def download_media():
    id = request.values["id"]

    try:
        uid = get_entity_id(Track, id)
    except GenericError:
        uid = None
    try:
        fid = get_entity_id(Folder, id)
    except GenericError:
        fid = None

    if uid is None and fid is None:
        raise GenericError("Invalid ID")

    if uid is not None:
        try:
            rv = Track[uid]
            return send_file(rv.path, mimetype=rv.mimetype, conditional=True)
        except Track.DoesNotExist:
            try:  # Album -> stream zipped tracks
                rv = Album[uid]
            except Album.DoesNotExist as e:
                raise NotFound("Track or Album") from e
    else:
        try:  # Folder -> stream zipped tracks, non recursive
            rv = Folder[fid]
        except Folder.DoesNotExist as e:
            raise NotFound("Folder") from e

    # Stream a zip of multiple files to the client
    z = ZipStream(sized=True)
    if isinstance(rv, Folder):
        # Add the entire folder tree to the zip
        z.add_path(rv.path, recurse=True)
    else:
        # Add tracks + cover art to the zip, preventing potential naming collisions
        seen = set()
        for track in rv.tracks:
            filename = os.path.basename(track.path)
            name, ext = os.path.splitext(filename)
            index = 0
            while filename in seen:
                index += 1
                filename = f"{name} ({index})"
                if ext:
                    filename += ext

            z.add_path(track.path, filename)
            seen.add(filename)

        cover_path = _cover_from_collection(rv, extract=False)
        if cover_path:
            z.add_path(cover_path)

    if not z:
        raise GenericError("Nothing to download")

    resp = Response(z, mimetype="application/zip")
    resp.headers["Content-Disposition"] = f"attachment; filename={rv.name}.zip"
    resp.headers["Content-Length"] = len(z)
    return resp


def _cover_from_track(obj):
    """Extract and return a path to a track's cover art

    Returns None if no cover art is available.
    """
    cache = current_app.cache
    cache_key = f"{obj.id}-cover"
    try:
        return cache.get(cache_key)
    except CacheMiss:
        try:
            return cache.set(cache_key, mediafile.MediaFile(obj.path).art)
        except mediafile.UnreadableFileError:
            return None


def _cover_from_collection(obj, extract=True):
    """Get a path to cover art from a collection (Album, Folder)

    If `extract` is True, will fall back to extracting cover art from tracks
    Returns None if no cover art is available.
    """
    cover_path = None

    if isinstance(obj, Folder) and obj.cover_art:
        cover_path = os.path.join(obj.path, obj.cover_art)

    elif isinstance(obj, Album):
        track_with_folder_cover = (
            obj.tracks.join(Folder, on=Track.folder)
            .where(Folder.cover_art.is_null(False))
            .first()
        )
        if track_with_folder_cover is not None:
            cover_path = _cover_from_collection(track_with_folder_cover.folder)

        if not cover_path and extract:
            track_with_embedded = obj.tracks.where(Track.has_art).first()
            if track_with_embedded is not None:
                cover_path = _cover_from_track(track_with_embedded.id)

    if not cover_path or not os.path.isfile(cover_path):
        return None
    return cover_path


def _get_cover_path(eid):
    try:
        fid = get_entity_id(Folder, eid)
    except GenericError:
        fid = None
    try:
        uid = get_entity_id(Track, eid)
    except GenericError:
        uid = None

    if not fid and not uid:
        raise GenericError("Invalid ID")

    if fid:
        try:
            return _cover_from_collection(Folder[fid])
        except Folder.DoesNotExist:
            pass
    elif uid:
        try:
            return _cover_from_track(Track[uid])
        except Track.DoesNotExist:
            pass

        try:
            return _cover_from_collection(Album[uid])
        except Album.DoesNotExist:
            pass

    raise NotFound("Entity")


@api_routing("/getCoverArt")
def cover_art():
    cache = current_app.cache

    eid = request.values["id"]
    cover_path = _get_cover_path(eid)

    if not cover_path:
        raise NotFound("Cover art")

    size = request.values.get("size")
    if size:
        size = int(size)
    else:
        # If the cover was extracted from a track it won't have an accurate
        # extension for Flask to derive the mimetype from - derive it from the
        # contents instead.
        mimetype = None
        if os.path.splitext(cover_path)[1].lower() not in EXTENSIONS:
            with Image.open(cover_path) as im:
                mimetype = f"image/{im.format.lower()}"
        return send_file(cover_path, mimetype=mimetype)

    with Image.open(cover_path) as im:
        mimetype = f"image/{im.format.lower()}"
        if size > im.width and size > im.height:
            return send_file(cover_path, mimetype=mimetype)

        cache_key = f"{eid}-cover-{size}"
        try:
            return send_file(cache.get(cache_key), mimetype=mimetype)
        except CacheMiss:
            im.thumbnail([size, size], Image.Resampling.LANCZOS)
            with cache.set_fileobj(cache_key) as fp:
                im.save(fp, im.format)
            return send_file(cache.get(cache_key), mimetype=mimetype)


def lyrics_response_for_track(track, lyrics):
    return request.formatter(
        "lyrics",
        {"artist": track.album.artist.name, "title": track.title, "value": lyrics},
    )


@api_routing("/getLyrics")
def lyrics():
    artist = request.values["artist"]
    title = request.values["title"]

    query = (
        Track.select()
        .join(Artist)
        .where(Track.title.contains(title), Artist.name.contains(artist))
    )
    for track in query:
        # Read from track metadata
        lyrics = mediafile.MediaFile(track.path).lyrics
        if lyrics is not None:
            lyrics = lyrics.replace("\x00", "").strip()
            if lyrics:
                logger.debug("Found lyrics in file metadata: " + track.path)
                return lyrics_response_for_track(track, lyrics)

        # Look for a text file with the same name of the track
        lyrics_path = os.path.splitext(track.path)[0] + ".txt"
        if os.path.exists(lyrics_path):
            logger.debug("Found lyrics file: " + lyrics_path)

            try:
                with open(lyrics_path) as f:
                    lyrics = f.read()
            except UnicodeError:
                # Lyrics file couldn't be decoded. Rather than displaying an error, try
                # with the potential next files or return no lyrics. Log it anyway.
                logger.warning("Unsupported encoding for lyrics file " + lyrics_path)
                continue

            return lyrics_response_for_track(track, lyrics)

    if not current_app.config["WEBAPP"]["online_lyrics"]:
        return request.formatter("lyrics", {})

    # Create a stable, unique, filesystem-compatible identifier for the artist+title
    unique = hashlib.md5(
        json.dumps([x.lower() for x in (artist, title)]).encode("utf-8")
    ).hexdigest()
    cache_key = f"lyrics-{unique}"

    lyrics = {}
    try:
        lyrics = json.loads(
            zlib.decompress(current_app.cache.get_value(cache_key)).decode("utf-8")
        )
    except (CacheMiss, zlib.error, TypeError, ValueError):
        try:
            r = requests.get(
                "http://api.chartlyrics.com/apiv1.asmx/SearchLyricDirect",
                params={"artist": artist, "song": title},
                timeout=5,
            )
            root = ElementTree.fromstring(r.content)

            ns = {"cl": "http://api.chartlyrics.com/"}
            lyrics = {
                "artist": root.find("cl:LyricArtist", namespaces=ns).text,
                "title": root.find("cl:LyricSong", namespaces=ns).text,
                "value": root.find("cl:Lyric", namespaces=ns).text,
            }

            current_app.cache.set(
                cache_key, zlib.compress(json.dumps(lyrics).encode("utf-8"), 9)
            )
        except requests.exceptions.RequestException as e:  # pragma: nocover
            logger.warning("Error while requesting the ChartLyrics API: " + str(e))

    return request.formatter("lyrics", lyrics)

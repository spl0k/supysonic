# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#               2018-2019 Carey 'pR0Ps' Metcalfe
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import mimetypes
import os.path
import shlex
import subprocess
from datetime import datetime
from io import BytesIO

from flask import Response, request, send_file
from PIL import Image
from zipstream import ZipStream

from ..app.flask import app_layer
from ..cache import CacheMiss
from ..covers import announce_covers
from ..covers._files import EXTENSIONS
from ..db.models import Album, Folder, Track
from ._blueprint import api_routing
from ._exceptions import (
    GenericError,
    NotFound,
    ServerError,
    UnsupportedParameter,
)
from ._helpers import get_bool, get_entity, get_format, get_int, resolve_child_id

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

    maxBitRate = get_int("maxBitRate", min=0)
    estimateContentLength = get_bool("estimateContentLength", False)
    request_format = get_format("format")

    src_suffix = res.suffix()
    dst_suffix = res.suffix()
    dst_bitrate = res.bitrate
    dst_mimetype = res.mimetype

    transcoding = app_layer.config.transcoding
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
        if dst_bitrate > maxBitRate:
            dst_bitrate = maxBitRate
            if using_default_format:
                dst_suffix = transcoding.default_transcode_target or dst_suffix

    # Find new mimetype if we're changing formats
    if dst_suffix != src_suffix:
        dst_mimetype = (
            mimetypes.guess_type("dummyname." + dst_suffix, False)[0]
            or "application/octet-stream"
        )

    if dst_suffix != src_suffix or dst_bitrate != res.bitrate:
        # Requires transcoding
        cache = app_layer.transcode_cache
        cache_key = f"{res.id}-{dst_bitrate}.{dst_suffix}"

        try:
            response = send_file(
                cache.get(cache_key), mimetype=dst_mimetype, conditional=True
            )
        except CacheMiss:
            transcoder, decoder, encoder = transcoding.resolve(src_suffix, dst_suffix)
            if not transcoder and not decoder:
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

            if estimateContentLength:
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
    res.last_play = datetime.now()
    res.save()

    user = request.user
    user.last_play = res
    user.last_play_date = datetime.now()
    user.save()

    return response


@api_routing("/download")
def download_media():
    cls, eid = resolve_child_id(request.values["id"])

    if cls is Track:
        try:
            rv = Track[eid]
            return send_file(rv.path, mimetype=rv.mimetype, conditional=True)
        except Track.DoesNotExist:
            try:  # Album -> stream zipped tracks
                rv = Album[eid]
            except Album.DoesNotExist as e:
                raise NotFound("Track or Album") from e
    else:
        try:  # Folder -> stream zipped tracks, non recursive
            rv = Folder[eid]
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

        _add_album_cover(z, rv)

    if not z:
        raise GenericError("Nothing to download")

    resp = Response(z, mimetype="application/zip")
    resp.headers.set("Content-Disposition", "attachment", filename=f"{rv.name}.zip")
    resp.headers.set("Content-Length", len(z))
    return resp


def _add_album_cover(z, album):
    """Add the cover announced for ``album`` to the zip ``z``, if any.

    Unless it belongs to a track: then it's embedded in a file already there.
    """

    announced = announce_covers(app_layer.cover_art_providers, [album])
    cover_id = announced.get(str(album.id))
    if cover_id is None:
        return

    entity = _get_cover_entity(cover_id)
    if isinstance(entity, Track):
        return

    cover = _get_cover(entity)
    if cover is None:
        return

    if cover.path is not None:
        z.add_path(cover.path)
    else:
        with Image.open(BytesIO(cover.data)) as im:
            z.add(cover.data, f"cover.{im.format.lower()}")


def _get_cover_entity(eid):
    """The entity a coverArt id names: a Folder, a Track or an Album."""

    cls, eid = resolve_child_id(eid)

    if cls is Folder:
        entity = Folder.get_or_none(id=eid)
    else:
        entity = Track.get_or_none(id=eid)
        if entity is None:
            entity = Album.get_or_none(id=eid)

    if entity is None:
        raise NotFound("Entity")
    return entity


def _get_cover(entity):
    """The cover belonging to ``entity``, from the first provider having one."""

    for provider in app_layer.cover_art_providers:
        cover = provider.get_cover(entity)
        if cover is not None:
            return cover

    return None


def _open_cover(cover):
    """What to give send_file or Image.open, a fresh one on every call."""
    return cover.path if cover.path is not None else BytesIO(cover.data)


@api_routing("/getCoverArt")
def cover_art():
    cache = app_layer.cache

    eid = request.values["id"]
    cover = _get_cover(_get_cover_entity(eid))

    if cover is None:
        raise NotFound("Cover art")

    size = get_int("size", min=1)
    if size is None:
        # Flask derives the mimetype from the extension of a file having a
        # meaningful one. Otherwise, as for raw data, derive it from the contents.
        if (
            cover.path is not None
            and os.path.splitext(cover.path)[1].lower() in EXTENSIONS
        ):
            return send_file(cover.path)

        with Image.open(_open_cover(cover)) as im:
            mimetype = f"image/{im.format.lower()}"
        return send_file(_open_cover(cover), mimetype=mimetype)

    with Image.open(_open_cover(cover)) as im:
        mimetype = f"image/{im.format.lower()}"
        if size > im.width and size > im.height:
            return send_file(_open_cover(cover), mimetype=mimetype)

        cache_key = f"{eid}-cover-{size}"
        try:
            return send_file(cache.get(cache_key), mimetype=mimetype)
        except CacheMiss:
            im.thumbnail([size, size], Image.Resampling.LANCZOS)
            with cache.set_fileobj(cache_key) as fp:
                im.save(fp, im.format)
            return send_file(cache.get(cache_key), mimetype=mimetype)


@api_routing("/getLyrics")
def lyrics():
    artist = request.values["artist"]
    title = request.values["title"]

    for provider in app_layer.lyrics_providers:
        found = provider.get_lyrics(artist, title)
        if found is not None:
            return request.formatter(
                "lyrics",
                {"artist": found.artist, "title": found.title, "value": found.text},
            )

    return request.formatter("lyrics", {})

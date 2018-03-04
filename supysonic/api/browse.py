# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import string
import uuid

from flask import request
from pony.orm import ObjectNotFound

from ..db import Folder, Artist, Album, Track
from ..py23 import dict

from . import api, get_entity

@api.route('/getMusicFolders.view', methods = [ 'GET', 'POST' ])
def list_folders():
    return request.formatter('musicFolders', dict(
        musicFolder = [ dict(
            id = str(f.id),
            name = f.name
        ) for f in Folder.select(lambda f: f.root).order_by(Folder.name) ]
    ))

@api.route('/getIndexes.view', methods = [ 'GET', 'POST' ])
def list_indexes():
    musicFolderId = request.values.get('musicFolderId')
    ifModifiedSince = request.values.get('ifModifiedSince')
    if ifModifiedSince:
        ifModifiedSince = int(ifModifiedSince) / 1000

    if musicFolderId is None:
        folders = Folder.select(lambda f: f.root)[:]
    else:
        mfid = uuid.UUID(musicFolderId)
        folder = Folder[mfid]
        if not folder.root:
            raise ObjectNotFound(Folder, mfid)

        folders = [ folder ]

    last_modif = max(map(lambda f: f.last_scan, folders))
    if ifModifiedSince is not None and last_modif < ifModifiedSince:
        return request.formatter('indexes', dict(lastModified = last_modif * 1000))

    # The XSD lies, we don't return artists but a directory structure
    artists = []
    children = []
    for f in folders:
        artists += f.children.select()[:]
        children += f.tracks.select()[:]

    indexes = dict()
    for artist in artists:
        index = artist.name[0].upper()
        if index in string.digits:
            index = '#'
        elif index not in string.ascii_letters:
            index = '?'

        if index not in indexes:
            indexes[index] = []

        indexes[index].append(artist)

    return request.formatter('indexes', dict(
        lastModified = last_modif * 1000,
        index = [ dict(
            name = k,
            artist = [ dict(
                id = str(a.id),
                name = a.name
            ) for a in sorted(v, key = lambda a: a.name.lower()) ]
        ) for k, v in sorted(indexes.items()) ],
        child = [ c.as_subsonic_child(request.user, request.client) for c in sorted(children, key = lambda t: t.sort_key()) ]
    ))

@api.route('/getMusicDirectory.view', methods = [ 'GET', 'POST' ])
def show_directory():
    res = get_entity(Folder)
    directory = dict(
        id = str(res.id),
        name = res.name,
        child = [ f.as_subsonic_child(request.user) for f in res.children.order_by(lambda c: c.name.lower()) ] + [ t.as_subsonic_child(request.user, request.client) for t in sorted(res.tracks, key = lambda t: t.sort_key()) ]
    )
    if not res.root:
        directory['parent'] = str(res.parent.id)

    return request.formatter('directory', directory)

@api.route('/getArtists.view', methods = [ 'GET', 'POST' ])
def list_artists():
    # According to the API page, there are no parameters?
    indexes = dict()
    for artist in Artist.select():
        index = artist.name[0].upper() if artist.name else '?'
        if index in string.digits:
            index = '#'
        elif index not in string.ascii_letters:
            index = '?'

        if index not in indexes:
            indexes[index] = []

        indexes[index].append(artist)

    return request.formatter('artists', dict(
        index = [ dict(
            name = k,
            artist = [ a.as_subsonic_artist(request.user) for a in sorted(v, key = lambda a: a.name.lower()) ]
        ) for k, v in sorted(indexes.items()) ]
    ))

@api.route('/getArtist.view', methods = [ 'GET', 'POST' ])
def artist_info():
    res = get_entity(Artist)
    info = res.as_subsonic_artist(request.user)
    albums  = set(res.albums)
    albums |= { t.album for t in res.tracks }
    info['album'] = [ a.as_subsonic_album(request.user) for a in sorted(albums, key = lambda a: a.sort_key()) ]

    return request.formatter('artist', info)

@api.route('/getAlbum.view', methods = [ 'GET', 'POST' ])
def album_info():
    res = get_entity(Album)
    info = res.as_subsonic_album(request.user)
    info['song'] = [ t.as_subsonic_child(request.user, request.client) for t in sorted(res.tracks, key = lambda t: t.sort_key()) ]

    return request.formatter('album', info)

@api.route('/getSong.view', methods = [ 'GET', 'POST' ])
def track_info():
    res = get_entity(Track)
    return request.formatter('song', res.as_subsonic_child(request.user, request.client))

@api.route('/getVideos.view', methods = [ 'GET', 'POST' ])
def list_videos():
    return request.formatter.error(0, 'Video streaming not supported'), 501


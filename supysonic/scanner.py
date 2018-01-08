# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2018  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, os.path
import mimetypes
import mutagen
import time

from pony.orm import db_session

from .db import Folder, Artist, Album, Track, User
from .db import StarredFolder, StarredArtist, StarredAlbum, StarredTrack
from .db import RatingFolder, RatingTrack
from .py23 import strtype

class Scanner:
    def __init__(self, force = False, extensions = None):
        if extensions is not None and not isinstance(extensions, list):
            raise TypeError('Invalid extensions type')

        self.__force = force

        self.__added_artists = 0
        self.__added_albums  = 0
        self.__added_tracks  = 0
        self.__deleted_artists = 0
        self.__deleted_albums  = 0
        self.__deleted_tracks  = 0

        self.__extensions = extensions

        self.__folders_to_check = set()
        self.__artists_to_check = set()
        self.__albums_to_check = set()

    def __del__(self):
        if self.__folders_to_check or self.__artists_to_check or self.__albums_to_check:
            raise Exception("There's still something to check. Did you run Scanner.finish()?")

    def scan(self, folder, progress_callback = None):
        if not isinstance(folder, Folder):
            raise TypeError('Expecting Folder instance, got ' + str(type(folder)))

        # Scan new/updated files
        files = [ os.path.join(root, f) for root, _, fs in os.walk(folder.path) for f in fs if self.__is_valid_path(os.path.join(root, f)) ]
        total = len(files)
        current = 0

        for path in files:
            self.scan_file(path)
            current += 1
            if progress_callback:
                progress_callback(current, total)

        # Remove files that have been deleted
        for track in Track.select(lambda t: t.root_folder == folder):
            if not self.__is_valid_path(track.path):
                self.remove_file(track.path)

        # Update cover art info
        folders = [ folder ]
        while folders:
            f = folders.pop()
            f.has_cover_art = os.path.isfile(os.path.join(f.path, 'cover.jpg'))
            folders += f.children

        folder.last_scan = int(time.time())

    @db_session
    def finish(self):
        for album in Album.select(lambda a: a.id in self.__albums_to_check):
            if not album.tracks.is_empty():
                continue

            self.__artists_to_check.add(album.artist.id)
            self.__deleted_albums += 1
            album.delete()
        self.__albums_to_check.clear()

        for artist in Artist.select(lambda a: a.id in self.__artists_to_check):
            if not artist.albums.is_empty() or not artist.tracks.is_empty():
                continue

            self.__deleted_artists += 1
            artist.delete()
        self.__artists_to_check.clear()

        while self.__folders_to_check:
            folder = Folder[self.__folders_to_check.pop()]
            if folder.root:
                continue

            if folder.tracks.is_empty() and folder.children.is_empty():
                self.__folders_to_check.add(folder.parent.id)
                folder.delete()

    def __is_valid_path(self, path):
        if not os.path.exists(path):
            return False
        if not self.__extensions:
            return True
        return os.path.splitext(path)[1][1:].lower() in self.__extensions

    @db_session
    def scan_file(self, path):
        if not isinstance(path, strtype):
            raise TypeError('Expecting string, got ' + str(type(path)))

        tr = Track.get(path = path)
        if tr is not None:
            if not self.__force and not int(os.path.getmtime(path)) > tr.last_modification:
                return

            tag = self.__try_load_tag(path)
            if not tag:
                self.remove_file(path)
                return
            trdict = {}
        else:
            tag = self.__try_load_tag(path)
            if not tag:
                return

            trdict = { 'path': path }

        artist = self.__try_read_tag(tag, 'artist')
        if not artist:
            return

        album       = self.__try_read_tag(tag, 'album', '[non-album tracks]')
        albumartist = self.__try_read_tag(tag, 'albumartist', artist)

        trdict['disc']     = self.__try_read_tag(tag, 'discnumber',  1, lambda x: int(x[0].split('/')[0]))
        trdict['number']   = self.__try_read_tag(tag, 'tracknumber', 1, lambda x: int(x[0].split('/')[0]))
        trdict['title']    = self.__try_read_tag(tag, 'title', '')
        trdict['year']     = self.__try_read_tag(tag, 'date', None, lambda x: int(x[0].split('-')[0]))
        trdict['genre']    = self.__try_read_tag(tag, 'genre')
        trdict['duration'] = int(tag.info.length)

        trdict['bitrate']  = (tag.info.bitrate if hasattr(tag.info, 'bitrate') else int(os.path.getsize(path) * 8 / tag.info.length)) / 1000
        trdict['content_type'] = mimetypes.guess_type(path, False)[0] or 'application/octet-stream'
        trdict['last_modification'] = int(os.path.getmtime(path))

        tralbum = self.__find_album(albumartist, album)
        trartist = self.__find_artist(artist)

        if tr is None:
            trdict['root_folder'] = self.__find_root_folder(path)
            trdict['folder'] = self.__find_folder(path)
            trdict['album'] = tralbum
            trdict['artist'] = trartist

            Track(**trdict)
            self.__added_tracks += 1
        else:
            if tr.album.id != tralbum.id:
                self.__albums_to_check.add(tr.album.id)
                trdict['album'] = tralbum

            if tr.artist.id != trartist.id:
                self.__artists_to_check.add(tr.artist.id)
                trdict['artist'] = trartist

            tr.set(**trdict)

    @db_session
    def remove_file(self, path):
        if not isinstance(path, strtype):
            raise TypeError('Expecting string, got ' + str(type(path)))

        tr = Track.get(path = path)
        if not tr:
            return

        self.__folders_to_check.add(tr.folder.id)
        self.__albums_to_check.add(tr.album.id)
        self.__artists_to_check.add(tr.artist.id)
        self.__deleted_tracks += 1
        tr.delete()

    @db_session
    def move_file(self, src_path, dst_path):
        if not isinstance(src_path, strtype):
            raise TypeError('Expecting string, got ' + str(type(src_path)))
        if not isinstance(dst_path, strtype):
            raise TypeError('Expecting string, got ' + str(type(dst_path)))

        if src_path == dst_path:
            return

        tr = Track.get(path = src_path)
        if tr is None:
            return

        self.__folders_to_check.add(tr.folder.id)
        tr_dst = Track.get(path = dst_path)
        if tr_dst is not None:
            root = tr_dst.root_folder
            folder = tr_dst.folder
            self.remove_file(dst_path)
            tr.root_folder = root
            tr.folder = folder
        else:
            root = self.__find_root_folder(dst_path)
            folder = self.__find_folder(dst_path)
            tr.root_folder = root
            tr.folder = folder
        tr.path = dst_path

    def __find_album(self, artist, album):
        ar = self.__find_artist(artist)
        al = ar.albums.select(lambda a: a.name == album).first()
        if al:
            return al

        al = Album(name = album, artist = ar)
        self.__added_albums += 1

        return al

    def __find_artist(self, artist):
        ar = Artist.get(name = artist)
        if ar:
            return ar

        ar = Artist(name = artist)
        self.__added_artists += 1

        return ar

    def __find_root_folder(self, path):
        path = os.path.dirname(path)
        for folder in Folder.select(lambda f: f.root):
            if path.startswith(folder.path):
                return folder

        raise Exception("Couldn't find the root folder for '{}'.\nDon't scan files that aren't located in a defined music folder".format(path))

    def __find_folder(self, path):
        children = []
        drive, _ = os.path.splitdrive(path)
        path = os.path.dirname(path)
        while path != drive and path != '/':
            folder = Folder.get(path = path)
            if folder is not None:
                break

            children.append(dict(root = False, name = os.path.basename(path), path = path))
            path = os.path.dirname(path)

        assert folder is not None
        while children:
            folder = Folder(parent = folder, **children.pop())

        return folder

    def __try_load_tag(self, path):
        try:
            return mutagen.File(path, easy = True)
        except:
            return None

    def __try_read_tag(self, metadata, field, default = None, transform = lambda x: x[0]):
        try:
            value = metadata[field]
            if not value:
                return default
            if transform:
                value = transform(value)
                return value if value else default
        except:
            return default

    def stats(self):
        return (self.__added_artists, self.__added_albums, self.__added_tracks), (self.__deleted_artists, self.__deleted_albums, self.__deleted_tracks)


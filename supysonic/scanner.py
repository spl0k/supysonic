# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2017  Alban 'spl0k' Féron
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

from .db import Folder, Artist, Album, Track, User
from .db import StarredFolder, StarredArtist, StarredAlbum, StarredTrack
from .db import RatingFolder, RatingTrack

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
        for track in [ t for t in self.__store.find(Track, Track.root_folder_id == folder.id) if not self.__is_valid_path(t.path) ]:
            self.remove_file(track.path)

        # Update cover art info
        folders = [ folder ]
        while folders:
            f = folders.pop()
            f.has_cover_art = os.path.isfile(os.path.join(f.path, 'cover.jpg'))
            folders += f.children

        folder.last_scan = int(time.time())

    def finish(self):
        for album in [ a for a in self.__albums_to_check if not a.tracks.count() ]:
            self.__artists_to_check.add(album.artist)
            self.__deleted_albums += 1
            album.delete()
        self.__albums_to_check.clear()

        for artist in [ a for a in self.__artists_to_check if not a.albums.count() and not a.tracks.count() ]:
            self.__deleted_artists += 1
            artist.delete()
        self.__artists_to_check.clear()

        while self.__folders_to_check:
            folder = self.__folders_to_check.pop()
            if folder.root:
                continue

            if not folder.tracks.count() and not folder.children.count():
                self.__folders_to_check.add(folder.parent)
                folder.delete()

    def __is_valid_path(self, path):
        if not os.path.exists(path):
            return False
        if not self.__extensions:
            return True
        return os.path.splitext(path)[1][1:].lower() in self.__extensions

    def scan_file(self, path):
        if not isinstance(path, basestring):
            raise TypeError('Expecting string, got ' + str(type(path)))

        tr = self.__store.find(Track, Track.path == path).one()
        add = False
        if tr:
            if not self.__force and not int(os.path.getmtime(path)) > tr.last_modification:
                return

            tag = self.__try_load_tag(path)
            if not tag:
                self.remove_file(path)
                return
        else:
            tag = self.__try_load_tag(path)
            if not tag:
                return

            tr = Track()
            tr.path = path
            add = True

        artist      = self.__try_read_tag(tag, 'artist', '')
        album       = self.__try_read_tag(tag, 'album', '')
        albumartist = self.__try_read_tag(tag, 'albumartist', artist)

        tr.disc     = self.__try_read_tag(tag, 'discnumber',  1, lambda x: int(x[0].split('/')[0]))
        tr.number   = self.__try_read_tag(tag, 'tracknumber', 1, lambda x: int(x[0].split('/')[0]))
        tr.title    = self.__try_read_tag(tag, 'title', '')
        tr.year     = self.__try_read_tag(tag, 'date', None, lambda x: int(x[0].split('-')[0]))
        tr.genre    = self.__try_read_tag(tag, 'genre')
        tr.duration = int(tag.info.length)

        tr.bitrate  = (tag.info.bitrate if hasattr(tag.info, 'bitrate') else int(os.path.getsize(path) * 8 / tag.info.length)) / 1000
        tr.content_type = mimetypes.guess_type(path, False)[0] or 'application/octet-stream'
        tr.last_modification = os.path.getmtime(path)

        tralbum = self.__find_album(albumartist, album)
        trartist = self.__find_artist(artist)

        if add:
            trroot = self.__find_root_folder(path)
            trfolder = self.__find_folder(path)

            # Set the references at the very last as searching for them will cause the added track to be flushed, even if
            # it is incomplete, causing not null constraints errors.
            tr.album = tralbum
            tr.artist = trartist
            tr.folder = trfolder
            tr.root_folder = trroot

            self.__store.add(tr)
            self.__added_tracks += 1
        else:
            if tr.album.id != tralbum.id:
                self.__albums_to_check.add(tr.album)
                tr.album = tralbum

            if tr.artist.id != trartist.id:
                self.__artists_to_check.add(tr.artist)
                tr.artist = trartist

    def remove_file(self, path):
        if not isinstance(path, basestring):
            raise TypeError('Expecting string, got ' + str(type(path)))

        tr = Track.get(path = path)
        if not tr:
            return

        self.__folders_to_check.add(tr.folder)
        self.__albums_to_check.add(tr.album)
        self.__artists_to_check.add(tr.artist)
        self.__deleted_tracks += 1
        tr.delete()

    def move_file(self, src_path, dst_path):
        if not isinstance(src_path, basestring):
            raise TypeError('Expecting string, got ' + str(type(src_path)))
        if not isinstance(dst_path, basestring):
            raise TypeError('Expecting string, got ' + str(type(dst_path)))

        if src_path == dst_path:
            return

        tr = self.__store.find(Track, Track.path == src_path).one()
        if not tr:
            return

        self.__folders_to_check.add(tr.folder)
        tr_dst = self.__store.find(Track, Track.path == dst_path).one()
        if tr_dst:
            tr.root_folder = tr_dst.root_folder
            tr.folder = tr_dst.folder
            self.remove_file(dst_path)
        else:
            root = self.__find_root_folder(dst_path)
            folder = self.__find_folder(dst_path)
            tr.root_folder = root
            tr.folder = folder
        tr.path = dst_path

    def __find_album(self, artist, album):
        ar = self.__find_artist(artist)
        al = ar.albums.find(name = album).one()
        if al:
            return al

        al = Album()
        al.name = album
        al.artist = ar

        self.__store.add(al)
        self.__added_albums += 1

        return al

    def __find_artist(self, artist):
        ar = self.__store.find(Artist, Artist.name == artist).one()
        if ar:
            return ar

        ar = Artist()
        ar.name = artist

        self.__store.add(ar)
        self.__added_artists += 1

        return ar

    def __find_root_folder(self, path):
        path = os.path.dirname(path)
        db = self.__store.get_database().__module__[len('storm.databases.'):]
        folders = self.__store.find(Folder, Like(path, Concat(Folder.path, u'%', db)), Folder.root == True)
        count = folders.count()
        if count > 1:
            raise Exception("Found multiple root folders for '{}'.".format(path))
        elif count == 0:
            raise Exception("Couldn't find the root folder for '{}'.\nDon't scan files that aren't located in a defined music folder".format(path))
        return folders.one()

    def __find_folder(self, path):
        path = os.path.dirname(path)
        folders = self.__store.find(Folder, Folder.path == path)
        count = folders.count()
        if count > 1:
            raise Exception("Found multiple folders for '{}'.".format(path))
        elif count == 1:
            return folders.one()

        db = self.__store.get_database().__module__[len('storm.databases.'):]
        folder = self.__store.find(Folder, Like(path, Concat(Folder.path, os.sep + u'%', db))).order_by(Folder.path).last()

        full_path = folder.path
        path = path[len(folder.path) + 1:]

        for name in path.split(os.sep):
            full_path = os.path.join(full_path, name)

            fold = Folder()
            fold.root = False
            fold.name = name
            fold.path = full_path
            fold.parent = folder

            self.__store.add(fold)

            folder = fold

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


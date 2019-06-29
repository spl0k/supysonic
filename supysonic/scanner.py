# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2019 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import os, os.path
import mutagen
import time

from datetime import datetime
from pony.orm import db_session
from threading import Thread, Event

from .covers import find_cover_in_folder, CoverFile
from .db import Folder, Artist, Album, Track, User
from .db import StarredFolder, StarredArtist, StarredAlbum, StarredTrack
from .db import RatingFolder, RatingTrack
from .py23 import strtype, Queue, QueueEmpty

logger = logging.getLogger(__name__)


class StatsDetails(object):
    def __init__(self):
        self.artists = 0
        self.albums = 0
        self.tracks = 0


class Stats(object):
    def __init__(self):
        self.scanned = 0
        self.added = StatsDetails()
        self.deleted = StatsDetails()
        self.errors = []


class ScanQueue(Queue):
    def _init(self, maxsize):
        self.queue = set()
        self.__last_got = None

    def _put(self, item):
        if self.__last_got != item:
            self.queue.add(item)

    def _get(self):
        self.__last_got = self.queue.pop()
        return self.__last_got


class Scanner(Thread):
    def __init__(
        self,
        force=False,
        extensions=None,
        progress=None,
        on_folder_start=None,
        on_folder_end=None,
        on_done=None,
    ):
        super(Scanner, self).__init__()

        if extensions is not None and not isinstance(extensions, list):
            raise TypeError("Invalid extensions type")

        self.__force = force
        self.__extensions = extensions

        self.__progress = progress
        self.__on_folder_start = on_folder_start
        self.__on_folder_end = on_folder_end
        self.__on_done = on_done

        self.__stopped = Event()
        self.__queue = ScanQueue()
        self.__stats = Stats()

    scanned = property(lambda self: self.__stats.scanned)

    def __report_progress(self, folder_name, scanned):
        if self.__progress is None:
            return

        self.__progress(folder_name, scanned)

    def queue_folder(self, folder_name):
        if not isinstance(folder_name, strtype):
            raise TypeError("Expecting string, got " + str(type(folder_name)))

        self.__queue.put(folder_name)

    def run(self):
        while not self.__stopped.is_set():
            try:
                folder_name = self.__queue.get(False)
            except QueueEmpty:
                break

            with db_session:
                folder = Folder.get(name=folder_name, root=True)
                if folder is None:
                    continue

            self.__scan_folder(folder)

        self.prune()

        if self.__on_done is not None:
            self.__on_done()

    def stop(self):
        self.__stopped.set()

    def __scan_folder(self, folder):
        logger.info("Scanning folder %s", folder.name)

        if self.__on_folder_start is not None:
            self.__on_folder_start(folder)

        # Scan new/updated files
        to_scan = [folder.path]
        scanned = 0
        while not self.__stopped.is_set() and to_scan:
            path = to_scan.pop()

            try:
                entries = os.listdir(path)
            except OSError:
                continue

            for f in entries:
                try:  # test for badly encoded filenames
                    f.encode("utf-8")
                except UnicodeError:
                    self.__stats.errors.append(path)
                    continue

                full_path = os.path.join(path, f)
                if os.path.islink(full_path):
                    continue
                elif os.path.isdir(full_path):
                    to_scan.append(full_path)
                elif os.path.isfile(full_path) and self.__is_valid_path(full_path):
                    self.scan_file(full_path)
                    self.__stats.scanned += 1
                    scanned += 1

                    self.__report_progress(folder.name, scanned)

        # Remove files that have been deleted
        if not self.__stopped.is_set():
            with db_session:
                for track in Track.select(lambda t: t.root_folder == folder):
                    if not self.__is_valid_path(track.path):
                        self.remove_file(track.path)

        # Remove deleted/moved folders and update cover art info
        folders = [folder]
        while not self.__stopped.is_set() and folders:
            f = folders.pop()

            with db_session:
                f = Folder[
                    f.id
                ]  # f has been fetched from another session, refetch or Pony will complain

                if not f.root and not os.path.isdir(f.path):
                    f.delete()  # Pony will cascade
                    continue

                self.find_cover(f.path)
                folders += f.children

        if not self.__stopped.is_set():
            with db_session:
                Folder[folder.id].last_scan = int(time.time())

        if self.__on_folder_end is not None:
            self.__on_folder_end(folder)

    def prune(self):
        if self.__stopped.is_set():
            return

        with db_session:
            self.__stats.deleted.albums = Album.prune()
            self.__stats.deleted.artists = Artist.prune()
            Folder.prune()

    def __is_valid_path(self, path):
        if not os.path.exists(path):
            return False
        if not self.__extensions:
            return True
        return os.path.splitext(path)[1][1:].lower() in self.__extensions

    @db_session
    def scan_file(self, path):
        if not isinstance(path, strtype):
            raise TypeError("Expecting string, got " + str(type(path)))

        tr = Track.get(path=path)
        mtime = (
            int(os.path.getmtime(path)) if os.path.exists(path) else 0
        )  # condition for some tests
        if tr is not None:
            if not self.__force and not mtime > tr.last_modification:
                return

            tag = self.__try_load_tag(path)
            if tag is None:
                self.remove_file(path)
                return
            trdict = {}
        else:
            tag = self.__try_load_tag(path)
            if tag is None:
                return

            trdict = {"path": path}

        artist = self.__try_read_tag(tag, "artist", "[unknown]")[:255]
        album = self.__try_read_tag(tag, "album", "[non-album tracks]")[:255]
        albumartist = self.__try_read_tag(tag, "albumartist", artist)[:255]

        trdict["disc"] = self.__try_read_tag(
            tag, "discnumber", 1, lambda x: int(x.split("/")[0])
        )
        trdict["number"] = self.__try_read_tag(
            tag, "tracknumber", 1, lambda x: int(x.split("/")[0])
        )
        trdict["title"] = self.__try_read_tag(tag, "title", os.path.basename(path))[
            :255
        ]
        trdict["year"] = self.__try_read_tag(
            tag, "date", None, lambda x: int(x.split("-")[0])
        )
        trdict["genre"] = self.__try_read_tag(tag, "genre")
        trdict["duration"] = int(tag.info.length)
        trdict["has_art"] = bool(Track._extract_cover_art(path))

        trdict["bitrate"] = (
            int(
                tag.info.bitrate
                if hasattr(tag.info, "bitrate")
                else os.path.getsize(path) * 8 / tag.info.length
            )
            // 1000
        )
        trdict["last_modification"] = mtime

        tralbum = self.__find_album(albumartist, album)
        trartist = self.__find_artist(artist)

        if tr is None:
            trdict["root_folder"] = self.__find_root_folder(path)
            trdict["folder"] = self.__find_folder(path)
            trdict["album"] = tralbum
            trdict["artist"] = trartist
            trdict["created"] = datetime.fromtimestamp(mtime)

            Track(**trdict)
            self.__stats.added.tracks += 1
        else:
            if tr.album.id != tralbum.id:
                trdict["album"] = tralbum

            if tr.artist.id != trartist.id:
                trdict["artist"] = trartist

            tr.set(**trdict)

    @db_session
    def remove_file(self, path):
        if not isinstance(path, strtype):
            raise TypeError("Expecting string, got " + str(type(path)))

        tr = Track.get(path=path)
        if not tr:
            return

        self.__stats.deleted.tracks += 1
        tr.delete()

    @db_session
    def move_file(self, src_path, dst_path):
        if not isinstance(src_path, strtype):
            raise TypeError("Expecting string, got " + str(type(src_path)))
        if not isinstance(dst_path, strtype):
            raise TypeError("Expecting string, got " + str(type(dst_path)))

        if src_path == dst_path:
            return

        tr = Track.get(path=src_path)
        if tr is None:
            return

        tr_dst = Track.get(path=dst_path)
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

    @db_session
    def find_cover(self, dirpath):
        if not isinstance(dirpath, strtype):  # pragma: nocover
            raise TypeError("Expecting string, got " + str(type(dirpath)))

        if not os.path.exists(dirpath):
            return

        folder = Folder.get(path=dirpath)
        if folder is None:
            return

        album_name = None
        track = folder.tracks.select().first()
        if track is not None:
            album_name = track.album.name

        cover = find_cover_in_folder(folder.path, album_name)
        folder.cover_art = cover.name if cover is not None else None

    @db_session
    def add_cover(self, path):
        if not isinstance(path, strtype):  # pragma: nocover
            raise TypeError("Expecting string, got " + str(type(path)))

        folder = Folder.get(path=os.path.dirname(path))
        if folder is None:
            return

        cover_name = os.path.basename(path)
        if not folder.cover_art:
            folder.cover_art = cover_name
        else:
            album_name = None
            track = folder.tracks.select().first()
            if track is not None:
                album_name = track.album.name

            current_cover = CoverFile(folder.cover_art, album_name)
            new_cover = CoverFile(cover_name, album_name)
            if new_cover.score > current_cover.score:
                folder.cover_art = cover_name

    def __find_album(self, artist, album):
        ar = self.__find_artist(artist)
        al = ar.albums.select(lambda a: a.name == album).first()
        if al:
            return al

        al = Album(name=album, artist=ar)
        self.__stats.added.albums += 1

        return al

    def __find_artist(self, artist):
        ar = Artist.get(name=artist)
        if ar:
            return ar

        ar = Artist(name=artist)
        self.__stats.added.artists += 1

        return ar

    def __find_root_folder(self, path):
        path = os.path.dirname(path)
        for folder in Folder.select(lambda f: f.root):
            if path.startswith(folder.path):
                return folder

        raise Exception(
            "Couldn't find the root folder for '{}'.\nDon't scan files that aren't located in a defined music folder".format(
                path
            )
        )

    def __find_folder(self, path):
        children = []
        drive, _ = os.path.splitdrive(path)
        path = os.path.dirname(path)
        while path != drive and path != "/":
            folder = Folder.get(path=path)
            if folder is not None:
                break

            created = datetime.fromtimestamp(os.path.getmtime(path))
            children.append(
                dict(
                    root=False, name=os.path.basename(path), path=path, created=created
                )
            )
            path = os.path.dirname(path)

        assert folder is not None
        while children:
            folder = Folder(parent=folder, **children.pop())

        return folder

    def __try_load_tag(self, path):
        try:
            return mutagen.File(path, easy=True)
        except mutagen.MutagenError:
            return None

    def __try_read_tag(self, metadata, field, default=None, transform=None):
        try:
            value = metadata[field][0]
            value = value.replace("\x00", "").strip()

            if not value:
                return default
            if transform:
                value = transform(value)
            return value if value else default
        # KeyError: missing tag
        # IndexError: tag is present but doesn't have any value
        # ValueError: tag can't be transformed to correct type
        except (KeyError, IndexError, ValueError):
            return default

    def stats(self):
        return self.__stats

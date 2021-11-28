# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging
import os
import os.path
import mediafile
import time

from datetime import datetime
from pony.orm import db_session
from queue import Queue, Empty as QueueEmpty
from threading import Thread, Event

from .covers import find_cover_in_folder, CoverFile
from .db import Folder, Artist, Album, Track


logger = logging.getLogger(__name__)


class StatsDetails:
    def __init__(self):
        self.artists = 0
        self.albums = 0
        self.tracks = 0


class Stats:
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
        follow_symlinks=False,
        progress=None,
        on_folder_start=None,
        on_folder_end=None,
        on_done=None,
    ):
        super().__init__()

        if extensions is not None and not isinstance(extensions, list):
            raise TypeError("Invalid extensions type")

        self.__force = force
        self.__extensions = extensions
        self.__follow_symlinks = follow_symlinks

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
        if not isinstance(folder_name, str):
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
            for entry in os.scandir(path):
                if entry.name.startswith("."):
                    continue
                if entry.is_symlink() and not self.__follow_symlinks:
                    continue
                elif entry.is_dir():
                    to_scan.append(entry.path)
                elif entry.is_file() and self.__check_extension(entry.path):
                    self.scan_file(entry)
                    self.__stats.scanned += 1
                    scanned += 1

                    self.__report_progress(folder.name, scanned)

        # Remove files that have been deleted
        # Could be more efficient if done above
        if not self.__stopped.is_set():
            with db_session:
                for track in Track.select(lambda t: t.root_folder == folder):
                    if not os.path.exists(track.path) or not self.__check_extension(
                        track.path
                    ):
                        self.remove_file(track.path)

        # Remove deleted/moved folders and update cover art info
        folders = [folder]
        while not self.__stopped.is_set() and folders:
            f = folders.pop()

            with db_session:
                # f has been fetched from another session, refetch or Pony will complain
                f = Folder[f.id]

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

    def __check_extension(self, path):
        if not self.__extensions:
            return True
        return os.path.splitext(path)[1][1:].lower() in self.__extensions

    @db_session
    def scan_file(self, path_or_direntry):
        if isinstance(path_or_direntry, str):
            path = path_or_direntry

            if not os.path.exists(path):
                return

            basename = os.path.basename(path)
            stat = os.stat(path)
        else:
            path = path_or_direntry.path
            basename = path_or_direntry.name
            stat = path_or_direntry.stat()

        try:
            path.encode("utf-8")  # Test for badly encoded paths
        except UnicodeError:
            self.__stats.errors.append(path)
            return

        mtime = int(stat.st_mtime)

        tr = Track.get(path=path)
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

        artist = (self.__sanitize_str(tag.artist) or "[unknown]")[:255]
        album = (self.__sanitize_str(tag.album) or "[non-album tracks]")[:255]
        albumartist = (self.__sanitize_str(tag.albumartist) or artist)[:255]

        trdict["disc"] = tag.disc or 1
        trdict["number"] = tag.track or 1
        trdict["title"] = (self.__sanitize_str(tag.title) or basename)[:255]
        trdict["year"] = tag.year
        trdict["genre"] = tag.genre
        trdict["duration"] = int(tag.length)
        trdict["has_art"] = bool(tag.images)

        trdict["bitrate"] = tag.bitrate
        trdict["last_modification"] = mtime

        tralbum = self.__find_album(albumartist, album)
        trartist = self.__find_artist(artist)

        if tr is None:
            trdict["root_folder"] = self.__find_root_folder(path)
            trdict["folder"] = self.__find_folder(path)
            trdict["album"] = tralbum
            trdict["artist"] = trartist
            trdict["created"] = datetime.fromtimestamp(mtime)

            try:
                Track(**trdict)
                self.__stats.added.tracks += 1
            except ValueError:
                # Field validation error
                self.__stats.errors.append(path)
        else:
            if tr.album.id != tralbum.id:
                trdict["album"] = tralbum

            if tr.artist.id != trartist.id:
                trdict["artist"] = trartist

            try:
                tr.set(**trdict)
            except ValueError:
                # Field validation error
                self.__stats.errors.append(path)

    @db_session
    def remove_file(self, path):
        if not isinstance(path, str):
            raise TypeError("Expecting string, got " + str(type(path)))

        tr = Track.get(path=path)
        if not tr:
            return

        self.__stats.deleted.tracks += 1
        tr.delete()

    @db_session
    def move_file(self, src_path, dst_path):
        if not isinstance(src_path, str):
            raise TypeError("Expecting string, got " + str(type(src_path)))
        if not isinstance(dst_path, str):
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
        if not isinstance(dirpath, str):  # pragma: nocover
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
        if not isinstance(path, str):  # pragma: nocover
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
        while path not in (drive, "/"):
            folder = Folder.get(path=path)
            if folder is not None:
                break

            created = datetime.fromtimestamp(os.path.getmtime(path))
            children.append(
                {
                    "root": False,
                    "name": os.path.basename(path),
                    "path": path,
                    "created": created,
                }
            )
            path = os.path.dirname(path)

        assert folder is not None
        while children:
            folder = Folder(parent=folder, **children.pop())

        return folder

    def __try_load_tag(self, path):
        try:
            return mediafile.MediaFile(path)
        except mediafile.UnreadableFileError:
            return None

    def __sanitize_str(self, value):
        if value is None:
            return None
        return value.replace("\x00", "").strip()

    def stats(self):
        return self.__stats

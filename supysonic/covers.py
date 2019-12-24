# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os.path
import re

from base64 import b64decode
from mutagen import File, FileType
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC, Picture
from mutagen._vorbis import VCommentDict
from PIL import Image
from os import scandir


EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")
NAMING_SCORE_RULES = (
    ("cover", 5),
    ("albumart", 5),
    ("folder", 5),
    ("front", 10),
    ("back", -10),
    ("large", 2),
    ("small", -2),
)


class CoverFile(object):
    __clean_regex = re.compile(r"[^a-z]")

    @staticmethod
    def __clean_name(name):
        return CoverFile.__clean_regex.sub("", name.lower())

    def __init__(self, name, album_name=None):
        self.name = name
        self.score = 0

        for part, score in NAMING_SCORE_RULES:
            if part in name.lower():
                self.score += score

        if album_name:
            basename, _ = os.path.splitext(name)
            clean = CoverFile.__clean_name(basename)
            album_name = CoverFile.__clean_name(album_name)
            if clean in album_name or album_name in clean:
                self.score += 20


def is_valid_cover(path):
    if not os.path.isfile(path):
        return False

    _, ext = os.path.splitext(path)
    if ext.lower() not in EXTENSIONS:
        return False

    try:  # Ensure the image can be read
        with Image.open(path):
            return True
    except IOError:
        return False


def find_cover_in_folder(path, album_name=None):
    if not os.path.isdir(path):
        raise ValueError("Invalid path")

    candidates = []
    for entry in scandir(path):
        if not is_valid_cover(entry.path):
            continue

        cover = CoverFile(entry.name, album_name)
        candidates.append(cover)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    return sorted(candidates, key=lambda c: c.score, reverse=True)[0]


def get_embedded_cover(path):
    if not isinstance(path, str):  # pragma: nocover
        raise TypeError("Expecting string, got " + str(type(path)))

    if not os.path.exists(path):
        return None

    metadata = File(path, easy=True)
    if not metadata:
        return None

    if isinstance(metadata.tags, EasyID3):
        picture = metadata["pictures"][0]
    elif isinstance(metadata, FLAC):
        picture = metadata.pictures[0]
    elif isinstance(metadata.tags, VCommentDict):
        picture = Picture(b64decode(metadata.tags["METADATA_BLOCK_PICTURE"][0]))
    else:
        return None

    return picture.data


def has_embedded_cover(metadata):
    if not isinstance(metadata, FileType):  # pragma: nocover
        raise TypeError("Expecting mutagen.FileType, got " + str(type(metadata)))

    pictures = []
    if isinstance(metadata.tags, EasyID3):
        pictures = metadata.get("pictures", [])
    elif isinstance(metadata, FLAC):
        pictures = metadata.pictures
    elif isinstance(metadata.tags, VCommentDict):
        pictures = metadata.tags.get("METADATA_BLOCK_PICTURE", [])

    return len(pictures) > 0


def _get_id3_apic(id3, key):
    return id3.getall("APIC")


EasyID3.RegisterKey("pictures", _get_id3_apic)

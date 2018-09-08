# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os, os.path
import re

from PIL import Image

EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp')
NAMING_SCORE_RULES = (
    ('cover',    5),
    ('albumart', 5),
    ('folder',   5),
    ('front',   10),
    ('back',   -10),
    ('large',    2),
    ('small',   -2)
)

class CoverFile(object):
    __clean_regex = re.compile(r'[^a-z]')
    @staticmethod
    def __clean_name(name):
        return CoverFile.__clean_regex.sub('', name.lower())

    def __init__(self, name, album_name = None):
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

    try: # Ensure the image can be read
        with Image.open(path):
            return True
    except IOError:
        return False

def find_cover_in_folder(path, album_name = None):
    if not os.path.isdir(path):
        raise ValueError('Invalid path')

    candidates = []
    for f in os.listdir(path):
        try:
            file_path = os.path.join(path, f)
        except UnicodeError:
            continue

        if not is_valid_cover(file_path):
            continue

        cover = CoverFile(f, album_name)
        candidates.append(cover)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    return sorted(candidates, key = lambda c: c.score, reverse = True)[0]


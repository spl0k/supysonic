# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

"""Shared test library for the browse and search API test cases.

The library is deliberately *irregular* so that endpoints which would otherwise
be indistinguishable can be told apart:

- The ``Rock`` folder holds both a subfolder (``Dark Side``) and a loose track
  (``Time``), exercising ``getMusicDirectory``'s mixed children ordering.
- Folder names (``Rock``/``Jazz``/...) differ from artist/album tag names, so the
  folder tree (``getIndexes``, ``search``/``search2``) diverges from the tag tree
  (``getArtists``, ``search3``).
- ``The Great Gig in the Sky`` (Clare Torry) and the ``Greatest Jazz Hits``
  compilation have tracks whose artist differs from their album's artist.
- Genres ``Rock`` and ``Jazz`` coexist with a null-genre track (``Blue in Green``).
"""

from types import SimpleNamespace

from supysonic.db import Folder, Artist, Album, Track

# Sanity totals, asserted by the callers after populating.
FOLDER_COUNT = 7
ROOT_COUNT = 2
ARTIST_COUNT = 4
ALBUM_COUNT = 3
TRACK_COUNT = 8


def populate_library():
    """Create the shared browse/search test library; return named references.

    Roots are created populated-first so AutoField ids are deterministic: the
    populated root is id 1, the empty root id 2 (matching ``musicFolderId`` 1/2).
    """

    # Roots (order matters: populated == 1, empty == 2)
    music = Folder.create(root=True, name="Music", path="tests/assets")
    empty = Folder.create(root=True, name="Empty root", path="/tmp")

    # Folder tree (names intentionally unrelated to artist/album tags)
    rock = Folder.create(
        name="Rock", path="tests/assets/Rock", root=False, parent=music
    )
    dark_side = Folder.create(
        name="Dark Side",
        path="tests/assets/Rock/DarkSide",
        root=False,
        parent=rock,
    )
    jazz = Folder.create(
        name="Jazz", path="tests/assets/Jazz", root=False, parent=music
    )
    kind_of_blue = Folder.create(
        name="Kind of Blue",
        path="tests/assets/Jazz/KindOfBlue",
        root=False,
        parent=jazz,
    )
    compilations = Folder.create(
        name="Compilations",
        path="tests/assets/Jazz/Compilations",
        root=False,
        parent=jazz,
    )

    # Artists (tags). "Various Artists" owns a compilation album but no tracks.
    pink_floyd = Artist.create(name="Pink Floyd")
    clare_torry = Artist.create(name="Clare Torry")
    miles_davis = Artist.create(name="Miles Davis")
    various = Artist.create(name="Various Artists")

    # Albums (tags)
    dsotm = Album.create(name="The Dark Side of the Moon", artist=pink_floyd)
    kob = Album.create(name="Kind of Blue", artist=miles_davis)
    greatest = Album.create(name="Greatest Jazz Hits", artist=various)

    def track(number, title, artist, album, folder, path, genre="Rock", year=1973):
        return Track.create(
            disc=1,
            number=number,
            title=title,
            duration=2,
            album=album,
            artist=artist,
            genre=genre,
            year=year,
            bitrate=320,
            path=path,
            last_modification=0,
            root_folder=music,
            folder=folder,
        )

    tracks = [
        # Dark Side album, in the "Dark Side" folder
        track(1, "Speak to Me", pink_floyd, dsotm, dark_side,
              "tests/assets/Rock/DarkSide/SpeakToMe"),
        # Guest vocalist: artist != album artist
        track(2, "The Great Gig in the Sky", clare_torry, dsotm, dark_side,
              "tests/assets/Rock/DarkSide/GreatGig"),
        track(3, "Money", pink_floyd, dsotm, dark_side,
              "tests/assets/Rock/DarkSide/Money"),
        # Same album, but physically loose in the parent "Rock" folder
        track(4, "Time", pink_floyd, dsotm, rock, "tests/assets/Rock/Time"),
        # Kind of Blue album, in the "Kind of Blue" folder
        track(5, "So What", miles_davis, kob, kind_of_blue,
              "tests/assets/Jazz/KindOfBlue/SoWhat", genre="Jazz", year=1959),
        # Null genre
        track(6, "Blue in Green", miles_davis, kob, kind_of_blue,
              "tests/assets/Jazz/KindOfBlue/BlueInGreen", genre=None, year=1959),
        # Compilation album: track artists differ from the album's "Various Artists"
        track(7, "Freddie Freeloader", miles_davis, greatest, compilations,
              "tests/assets/Jazz/Compilations/FreddieFreeloader",
              genre="Jazz", year=1959),
        track(8, "Money (Live)", pink_floyd, greatest, compilations,
              "tests/assets/Jazz/Compilations/MoneyLive", genre="Rock", year=None),
    ]

    return SimpleNamespace(
        root=music,
        empty_root=empty,
        folders=SimpleNamespace(
            music=music,
            empty=empty,
            rock=rock,
            dark_side=dark_side,
            jazz=jazz,
            kind_of_blue=kind_of_blue,
            compilations=compilations,
        ),
        artists=SimpleNamespace(
            pink_floyd=pink_floyd,
            clare_torry=clare_torry,
            miles_davis=miles_davis,
            various=various,
        ),
        albums=SimpleNamespace(dsotm=dsotm, kob=kob, greatest=greatest),
        tracks=tracks,
    )

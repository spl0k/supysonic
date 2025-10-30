# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2025 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

# Converts comma-separated playlists

import sqlite3
import uuid

static_queries = (
    """CREATE TABLE IF NOT EXISTS playlist_track (
        id CHAR(36) PRIMARY KEY,
        playlist_id CHAR(36) NOT NULL REFERENCES playlist,
        track_id CHAR(36) NOT NULL REFERENCES track,
        "index" INTEGER NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS index_playlist_track_playlist_id_fk ON playlist_track(playlist_id)",
    "CREATE INDEX IF NOT EXISTS index_playlist_track_track_id_fk ON playlist_track(track_id)",
)


def apply(args):
    file = args.pop("database")
    with sqlite3.connect(file, **args) as conn:
        c = conn.cursor()

        for query in static_queries:
            c.execute(query)
        conn.commit()

        for id, tracks in c.execute("SELECT id, tracks FROM playlist"):
            params = []
            for idx, trackid in enumerate(tracks.split(",")):
                params.append((uuid.uuid4().hex, id, uuid.UUID(trackid).hex, idx))
            sql = 'INSERT INTO playlist_track(id, playlist_id, track_id, "index") VALUES(?, ?, ?, ?)'
            c.executemany(sql, params)
        conn.commit()

        c.execute("ALTER TABLE playlist DROP COLUMN tracks")
        conn.commit()

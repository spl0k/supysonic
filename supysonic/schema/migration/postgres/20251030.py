# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2025 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

# Converts comma-separated playlists

import psycopg2
import uuid

static_queries = (
    """CREATE TABLE IF NOT EXISTS playlist_track (
        id UUID PRIMARY KEY,
        playlist_id UUID NOT NULL REFERENCES playlist,
        track_id UUID NOT NULL REFERENCES track,
        "index" INTEGER NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS index_playlist_track_playlist_id_fk ON playlist_track(playlist_id)",
    "CREATE INDEX IF NOT EXISTS index_playlist_track_track_id_fk ON playlist_track(track_id)",
)


def apply(args):
    with psycopg2.connect(**args) as conn:
        c = conn.cursor()

        for query in static_queries:
            c.execute(query)
        conn.commit()

        c2 = conn.cursor()
        c2.execute("SELECT id, tracks FROM playlist")
        for id, tracks in c2:
            params = []
            for idx, trackid in enumerate(tracks.split(",")):
                params.append((uuid.uuid4(), id, uuid.UUID(trackid), idx))
            sql = 'INSERT INTO playlist_track(id, playlist_id, track_id, "index") VALUES(%s, %s, %s, %s) ON CONFLICT DO NOTHING'
            c.executemany(sql, params)
        conn.commit()

        c.execute("ALTER TABLE playlist DROP COLUMN tracks")
        conn.commit()

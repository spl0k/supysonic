# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2025 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

# Converts comma-separated playlists

try:
    import MySQLdb as provider
except ImportError:
    import pymysql as provider
import uuid

static_queries = (
    """CREATE TABLE IF NOT EXISTS playlist_track (
        id CHAR(32) PRIMARY KEY,
        playlist_id CHAR(32) NOT NULL REFERENCES playlist(id),
        track_id CHAR(32) NOT NULL REFERENCES track(id),
        `index` INTEGER NOT NULL
    ) DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci""",
    "CREATE INDEX index_playlist_track_playlist_id_fk ON playlist_track(playlist_id)",
    "CREATE INDEX index_playlist_track_track_id_fk ON playlist_track(track_id)",
)


def apply(args):
    with provider.connect(**args) as conn:
        c = conn.cursor()

        for query in static_queries:
            c.execute(query)
        conn.commit()

        c2 = conn.cursor()
        c2.execute("SELECT id, tracks FROM playlist")
        for id, tracks in c2:
            params = []
            for idx, trackid in enumerate(tracks.split(",")):
                params.append((uuid.uuid4().hex, id, uuid.UUID(trackid).hex, idx))
            sql = "INSERT IGNORE INTO playlist_track(id, playlist_id, track_id, `index`) VALUES(%s, %s, %s, %s)"
            c.executemany(sql, params)
        conn.commit()

        c.execute("ALTER TABLE playlist DROP COLUMN tracks")
        conn.commit()

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

# Converts ids from binary data to hex-encoded strings

import sqlite3

from uuid import UUID


def process_table(connection, table, fields):
    to_update = {field: set() for field in fields}

    c = connection.cursor()
    for row in c.execute("SELECT {1} FROM {0}".format(table, ",".join(fields))):
        for field, value in zip(fields, row):
            if value is None or not isinstance(value, bytes):
                continue
            to_update[field].add(value)

    for field, values in to_update.items():
        sql = "UPDATE {0} SET {1}=? WHERE {1}=?".format(table, field)
        c.executemany(sql, map(lambda v: (UUID(bytes=v).hex, v), values))

    connection.commit()


def apply(args):
    file = args.pop("database")
    with sqlite3.connect(file, **args) as conn:
        conn.cursor().execute("PRAGMA foreign_keys = OFF")

        process_table(conn, "artist", ("id",))
        process_table(conn, "album", ("id", "artist_id"))
        process_table(conn, "track", ("id", "album_id", "artist_id"))
        process_table(conn, "user", ("id", "last_play_id"))
        process_table(conn, "client_prefs", ("user_id",))
        process_table(conn, "starred_folder", ("user_id",))
        process_table(conn, "starred_artist", ("user_id", "starred_id"))
        process_table(conn, "starred_album", ("user_id", "starred_id"))
        process_table(conn, "starred_track", ("user_id", "starred_id"))
        process_table(conn, "rating_folder", ("user_id",))
        process_table(conn, "rating_track", ("user_id", "rated_id"))
        process_table(conn, "chat_message", ("id", "user_id"))
        process_table(conn, "playlist", ("id", "user_id"))
        process_table(conn, "radio_station", ("id",))

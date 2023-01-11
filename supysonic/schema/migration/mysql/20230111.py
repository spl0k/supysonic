# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2023 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

# Converts ids from binary data to hex-encoded strings

try:
    import MySQLdb as provider
except ImportError:
    import pymysql as provider

from uuid import UUID
from warnings import filterwarnings


def process_table(connection, table, fields, nullable_fields=()):
    to_update = {field: set() for field in fields + nullable_fields}

    c = connection.cursor()
    c.execute("SELECT {1} FROM {0}".format(table, ",".join(fields + nullable_fields)))
    for row in c:
        for field, value in zip(fields + nullable_fields, row):
            if value is None or not isinstance(value, bytes):
                continue
            to_update[field].add(value)

    for field in fields:
        sql = "ALTER TABLE {} MODIFY {} BINARY(32) NOT NULL".format(table, field)
        c.execute(sql)
    for field in nullable_fields:
        sql = "ALTER TABLE {} MODIFY {} BINARY(32)".format(table, field)
        c.execute(sql)
    for field, values in to_update.items():
        if not values:
            continue
        sql = "UPDATE {0} SET {1}=%s WHERE {1}=%s".format(table, field)
        c.executemany(
            sql, map(lambda v: (UUID(bytes=v).hex, v + (b"\x00" * 16)), values)
        )
    for field in fields:
        sql = "ALTER TABLE {} MODIFY {} CHAR(32) NOT NULL".format(table, field)
        c.execute(sql)
    for field in nullable_fields:
        sql = "ALTER TABLE {} MODIFY {} CHAR(32)".format(table, field)
        c.execute(sql)

    connection.commit()


def apply(args):
    filterwarnings("ignore", category=provider.Warning)

    conn = provider.connect(**args)
    conn.cursor().execute("SET FOREIGN_KEY_CHECKS = 0")

    process_table(conn, "artist", ("id",))
    process_table(conn, "album", ("id", "artist_id"))
    process_table(conn, "track", ("id", "album_id", "artist_id"))
    process_table(conn, "user", ("id",), ("last_play_id",))
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

    conn.cursor().execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.close()

# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

# Converts ids from hex-encoded strings to binary data

import argparse

try:
    import MySQLdb as provider
except ImportError:
    import pymysql as provider

from uuid import UUID
from warnings import filterwarnings

parser = argparse.ArgumentParser()
parser.add_argument("username")
parser.add_argument("password")
parser.add_argument("database")
parser.add_argument("-H", "--host", default="localhost", help="default: localhost")
args = parser.parse_args()


def process_table(connection, table, fields, nullable_fields=()):
    to_update = {field: set() for field in fields + nullable_fields}

    c = connection.cursor()
    c.execute("SELECT {1} FROM {0}".format(table, ",".join(fields + nullable_fields)))
    for row in c:
        for field, value in zip(fields + nullable_fields, row):
            if value is None or not isinstance(value, str):
                continue
            to_update[field].add(value)

    for field, values in to_update.iteritems():
        if not values:
            continue
        sql = "UPDATE {0} SET {1}=%s WHERE {1}=%s".format(table, field)
        c.executemany(sql, map(lambda v: (UUID(v).bytes, v), values))
    for field in fields:
        sql = "ALTER TABLE {} MODIFY {} BINARY(16) NOT NULL".format(table, field)
        c.execute(sql)
    for field in nullable_fields:
        sql = "ALTER TABLE {} MODIFY {} BINARY(16)".format(table, field)
        c.execute(sql)

    connection.commit()


filterwarnings("ignore", category=provider.Warning)
conn = provider.connect(
    host=args.host, user=args.username, passwd=args.password, db=args.database
)
conn.cursor().execute("SET FOREIGN_KEY_CHECKS = 0")

process_table(conn, "folder", ("id",), ("parent_id",))
process_table(conn, "artist", ("id",))
process_table(conn, "album", ("id", "artist_id"))
process_table(
    conn, "track", ("id", "album_id", "artist_id", "root_folder_id", "folder_id")
)
process_table(conn, "user", ("id",), ("last_play_id",))
process_table(conn, "client_prefs", ("user_id",))
process_table(conn, "starred_folder", ("user_id", "starred_id"))
process_table(conn, "starred_artist", ("user_id", "starred_id"))
process_table(conn, "starred_album", ("user_id", "starred_id"))
process_table(conn, "starred_track", ("user_id", "starred_id"))
process_table(conn, "rating_folder", ("user_id", "rated_id"))
process_table(conn, "rating_track", ("user_id", "rated_id"))
process_table(conn, "chat_message", ("id", "user_id"))
process_table(conn, "playlist", ("id", "user_id"))

conn.cursor().execute("SET FOREIGN_KEY_CHECKS = 1")
conn.close()

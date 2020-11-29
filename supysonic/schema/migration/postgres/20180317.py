import argparse
import hashlib
import psycopg2

try:
    bytes = buffer
except NameError:
    pass

parser = argparse.ArgumentParser()
parser.add_argument("username")
parser.add_argument("password")
parser.add_argument("database")
parser.add_argument("-H", "--host", default="localhost", help="default: localhost")
args = parser.parse_args()


def process_table(connection, table):
    c = connection.cursor()

    c.execute(
        r"ALTER TABLE {} ADD COLUMN path_hash BYTEA NOT NULL DEFAULT E'\\0000'".format(
            table
        )
    )

    hashes = dict()
    c.execute("SELECT path FROM {}".format(table))
    for row in c.fetchall():
        hashes[row[0]] = hashlib.sha1(row[0].encode("utf-8")).digest()
    c.executemany(
        "UPDATE {} SET path_hash=%s WHERE path=%s".format(table),
        [(bytes(h), p) for p, h in hashes.items()],
    )

    c.execute("CREATE UNIQUE INDEX index_{0}_path ON {0}(path_hash)".format(table))


with psycopg2.connect(
    host=args.host, user=args.username, password=args.password, dbname=args.database
) as conn:
    process_table(conn, "folder")
    process_table(conn, "track")

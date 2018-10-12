import argparse
import psycopg2
from supysonic import db

parser = argparse.ArgumentParser()
parser.add_argument('username')
parser.add_argument('password')
parser.add_argument('database')
parser.add_argument('-H', '--host', default = 'localhost', help = 'default: localhost')
args = parser.parse_args()

with psycopg2.connect(host = args.host, user = args.username, password = args.password, dbname = args.database) as conn:
    c = conn.cursor()
    c.execute('ALTER TABLE track ADD COLUMN has_art BOOLEAN NOT NULL DEFAULT false')

    art = dict()
    c.execute('SELECT path FROM track')
    for row in c.fetchall():
        art[row[0]] = bool(db.Track._extract_cover_art(row[0].encode('utf-8')))
    c.executemany('UPDATE track SET has_art=%s WHERE path=%s', [ (a, p) for p, a in art.items() ])
    conn.commit()

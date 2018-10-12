import argparse
import sqlite3
from supysonic import db

parser = argparse.ArgumentParser()
parser.add_argument('dbfile', help = 'Path to the SQLite database file')
args = parser.parse_args()

with sqlite3.connect(args.dbfile) as conn:
    c = conn.cursor()
    c.execute('ALTER TABLE track ADD COLUMN has_art BOOLEAN NOT NULL DEFAULT false')

    art = dict()
    for row in c.execute('SELECT path FROM track'):
        art[row[0]] = bool(db.Track._extract_cover_art(row[0].encode('utf-8')))
    c.executemany('UPDATE track SET has_art=? WHERE path=?', [ (a, p) for p, a in art.items() ])
    conn.commit()
    conn.execute('VACUUM')

import argparse
from supysonic import db
try:
    import MySQLdb as provider
except ImportError:
    import pymysql as provider

parser = argparse.ArgumentParser()
parser.add_argument('username')
parser.add_argument('password')
parser.add_argument('database')
parser.add_argument('-H', '--host', default = 'localhost', help = 'default: localhost')
args = parser.parse_args()

with provider.connect(host = args.host, user = args.username, passwd = args.password, db = args.database) as conn:
    c = conn.cursor()
    c.execute('ALTER TABLE track ADD COLUMN has_art BOOLEAN NOT NULL DEFAULT false')

    art = dict()
	c.execute('SELECT path FROM track')
    for row in c:
        art[row[0]] = bool(db.Track._extract_cover_art(row[0].encode('utf-8')))
    c.executemany('UPDATE track SET has_art=? WHERE path=?', [ (a, p) for p, a in art.items() ])
    conn.commit()

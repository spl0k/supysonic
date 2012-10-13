# coding: utf-8

from web import app
import db, config

if __name__ == '__main__':
	if not config.check():
		print >>sys.stderr, "Couldn't find configuration file"
		sys.exit(1)

	db.init_db()
	app.run(debug = True)


# coding: utf-8

import config
import os.path, sys

if __name__ == '__main__':
	if not config.check():
		print >>sys.stderr, "Couldn't find configuration file"
		sys.exit(1)

	if not os.path.exists(config.get('CACHE_DIR')):
		os.makedirs(config.get('CACHE_DIR'))

	import db
	from web import app

	db.init_db()
	app.run(debug = True)


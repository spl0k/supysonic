# coding: utf-8

import config
import os.path, sys

if __name__ == '__main__':
	if not config.check():
		sys.exit(1)

	if not os.path.exists(config.get('base', 'cache_dir')):
		os.makedirs(config.get('base', 'cache_dir'))

	import db
	from web import app

	db.init_db()
	app.run(host = '0.0.0.0', debug = True)


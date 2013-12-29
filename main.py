# coding: utf-8

import config
import os.path, sys

if __name__ == '__main__':
	if not config.check():
		sys.exit(1)

	if not os.path.exists(config.get('base', 'cache_dir')):
		os.makedirs(config.get('base', 'cache_dir'))

	from web import app

	app.run(host = '0.0.0.0')


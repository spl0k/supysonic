# coding: utf-8

import os.path, sys
sys.path.insert(0, '/path/to/the/supysonic/app')

import config
if not config.check():
	sys.exit(1)

if not os.path.exists(config.get('base', 'cache_dir')):
	os.makedirs(config.get('base', 'cache_dir'))

import db
db.init_db()

from web import app as application


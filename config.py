# coding: utf-8

import os, sys, tempfile, ConfigParser

config = ConfigParser.RawConfigParser({ 'cache_dir': os.path.join(tempfile.gettempdir(), 'supysonic') })

def check():
	try:
		ret = config.read([ '/etc/supysonic', os.path.expanduser('~/.supysonic') ])
	except (ConfigParser.MissingSectionHeaderError, ConfigParser.ParsingError), e:
		print >>sys.stderr, "Error while parsing the configuration file(s):\n%s" % str(e)
		return False

	if not ret:
		print >>sys.stderr, "No configuration file found"
		return False

	try:
		config.get('base', 'database_uri')
	except:
		print >>sys.stderr, "No database URI set"
		return False

	return True

def get(section, name):
	try:
		return config.get(section, name)
	except:
		return None


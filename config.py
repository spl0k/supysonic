# coding: utf-8

import os

def check():
	path = os.path.join(os.path.expanduser('~'), '.supysonic')
	if os.path.exists(path):
		return path
	path = '/etc/supysonic'
	if os.path.exists(path):
		return path
	return False

config_path = check()
config_dict = {}
if config_path:
	with open(config_path) as f:
		for line in f:
			spl = line.split('=')
			config_dict[spl[0].strip()] = eval(spl[1])

def get(name):
	return config_dict.get(name)

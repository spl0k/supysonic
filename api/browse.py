# coding: utf-8

from flask import request
from web import app
from db import MusicFolder

@app.route('/rest/getMusicFolders.view')
def list_folders():
	return request.formatter({
		'musicFolders': {
			'musicFolder': [ {
				'id': str(f.id),
				'name': f.name
			} for f in MusicFolder.query.order_by(MusicFolder.name).all() ]
		}
	})


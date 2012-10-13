# coding: utf-8

from flask import request
from web import app

@app.route('/rest/ping.view')
def ping():
	return request.formatter({})

@app.route('/rest/getLicense.view')
def license():
	return request.formatter({ 'license': { 'valid': False } })


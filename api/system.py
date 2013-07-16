# coding: utf-8

from flask import request
from web import app

@app.route('/rest/ping.view', methods = [ 'GET', 'POST' ])
def ping():
	return request.formatter({})

@app.route('/rest/getLicense.view', methods = [ 'GET', 'POST' ])
def license():
	return request.formatter({ 'license': { 'valid': True } })


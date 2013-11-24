# coding: utf-8

from flask import request
from xml.etree import ElementTree
import simplejson
import uuid

from web import app
from managers.user import UserManager

@app.before_request
def set_formatter():
	if not request.path.startswith('/rest/'):
		return

	"""Return a function to create the response."""
	(f, callback) = map(request.args.get, ['f', 'callback'])
	if f == 'jsonp':
		# Some clients (MiniSub, Perisonic) set f to jsonp without callback for streamed data
		if not callback and request.endpoint not in [ 'stream_media', 'cover_art' ]:
			return ResponseHelper.responsize_json({
				'error': {
					'code': 0,
					'message': 'Missing callback'
				}
			}, error = True), 400
		request.formatter = lambda x, **kwargs: ResponseHelper.responsize_jsonp(x, callback, kwargs)
	elif f == "json":
		request.formatter = ResponseHelper.responsize_json
	else:
		request.formatter = ResponseHelper.responsize_xml

	request.error_formatter = lambda code, msg: request.formatter({ 'error': { 'code': code, 'message': msg } }, error = True)

@app.before_request
def authorize():
	if not request.path.startswith('/rest/'):
		return

	error = request.error_formatter(40, 'Unauthorized'), 401

	if request.authorization:
		status, user = UserManager.try_auth(request.authorization.username, request.authorization.password)
		if status == UserManager.SUCCESS:
			request.username = request.authorization.username
			request.user = user
			return

	(username, password) = map(request.args.get, [ 'u', 'p' ])
	if not username or not password:
		return error

	status, user = UserManager.try_auth(username, password)
	if status != UserManager.SUCCESS:
		return error

	request.username = username
	request.user = user

@app.after_request
def set_content_type(response):
	if not request.path.startswith('/rest/'):
		return response

	if response.mimetype.startswith('text'):
		f = request.args.get('f')
		response.headers['content-type'] = 'application/json' if f in [ 'jsonp', 'json' ] else 'text/xml'

	return response

@app.errorhandler(404)
def not_found(error):
	if not request.path.startswith('/rest/'):
		return error

	return request.error_formatter(0, 'Not implemented'), 501

class ResponseHelper:

	@staticmethod
	def responsize_json(ret, error = False, version = "1.8.0"):
		def check_lists(d):
			for key, value in d.items():
				if isinstance(value, dict):
					d[key] = check_lists(value)
				elif isinstance(value, list):
					if len(value) == 0:
						del d[key]
					else:
						d[key] = [ check_lists(item) if isinstance(item, dict) else item for item in value ]
			return d

		ret = check_lists(ret)
		# add headers to response
		ret.update({
			'status': 'failed' if error else 'ok',
			'version': version,
			'xmlns': "http://subsonic.org/restapi"
		})
		return simplejson.dumps({ 'subsonic-response': ret }, indent = True, encoding = 'utf-8')

	@staticmethod
	def responsize_jsonp(ret, callback, error = False, version = "1.8.0"):
		return "%s(%s)" % (callback, ResponseHelper.responsize_json(ret, error, version))

	@staticmethod
	def responsize_xml(ret, error = False, version = "1.8.0"):
		"""Return an xml response from json and replace unsupported characters."""
		ret.update({
			'status': 'failed' if error else 'ok',
			'version': version,
			'xmlns': "http://subsonic.org/restapi"
		})

		elem = ElementTree.Element('subsonic-response')
		ResponseHelper.dict2xml(elem, ret)

		return '<?xml version="1.0" encoding="UTF-8" ?>' + ElementTree.tostring(elem, 'utf-8')

	@staticmethod
	def dict2xml(elem, dictionary):
		"""Convert a json structure to xml. The game is trivial. Nesting uses the [] parenthesis.
		  ex.  { 'musicFolder': {'id': 1234, 'name': "sss" } }
			ex. { 'musicFolder': [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }]}
			ex. { 'musicFolders': {'musicFolder' : [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }] } }
			ex. { 'index': [{'name': 'A',  'artist': [{'id': '517674445', 'name': 'Antonello Venditti'}] }] }
			ex. {"subsonic-response": { "musicFolders": {"musicFolder": [{ "id": 0,"name": "Music"}]},
			"status": "ok","version": "1.7.0","xmlns": "http://subsonic.org/restapi"}}
				"""
		if not isinstance(dictionary, dict):
			raise TypeError('Expecting a dict')

		subelems =   { k: v for k, v in dictionary.iteritems() if isinstance(v, dict) }
		sequences =  { k: v for k, v in dictionary.iteritems() if isinstance(v, list) }
		attributes = { k: v for k, v in dictionary.iteritems() if k != '_value_' and k not in subelems and k not in sequences }

		if '_value_' in dictionary:
			elem.text = dictionary['_value_']
		for attr, value in attributes.iteritems():
			elem.set(attr, str(value).lower() if isinstance(value, bool) else str(value))
		for sub, subdict in subelems.iteritems():
			subelem = ElementTree.SubElement(elem, sub)
			ResponseHelper.dict2xml(subelem, subdict)
		for seq, dicts in sequences.iteritems():
			for subdict in dicts:
				subelem = ElementTree.SubElement(elem, seq)
				ResponseHelper.dict2xml(subelem, subdict)

def get_entity(req, ent, param = 'id'):
	eid = req.args.get(param)
	if not eid:
		return False, req.error_formatter(10, 'Missing %s id' % ent.__name__)

	try:
		eid = uuid.UUID(eid)
	except:
		return False, req.error_formatter(0, 'Invalid %s id' % ent.__name__)

	entity = ent.query.get(eid)
	if not entity:
		return False, (req.error_formatter(70, '%s not found' % ent.__name__), 404)

	return True, entity


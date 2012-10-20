# coding: utf-8

from flask import request
import simplejson
import cgi

from web import app
from db import User
import hashlib

@app.before_request
def set_formatter():
	if not request.path.startswith('/rest/'):
		return

	"""Return a function to create the response."""
	(f, callback) = map(request.args.get, ['f', 'callback'])
	if f == 'jsonp':
		# Some clients (MiniSub, Perisonic) set f to jsonp without callback for streamed data
		if not callback and request.endpoint not in [ 'stream_media' ]:
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

@app.before_request
def authorize():
	if not request.path.startswith('/rest/'):
		return

	error = request.formatter({
		'error': {
			'code': 40,
			'message': 'Unauthorized'
		}
	}, error = True), 401

	(username, decoded_pass) = map(request.args.get, [ 'u', 'p' ])
	if not username or not decoded_pass:
		return error

	user = User.query.filter(User.name == username).first()
	if not user:
		return error

	if decoded_pass.startswith('enc:'):
		decoded_pass = hexdecode(decoded_pass[4:])
	
	crypt = hashlib.sha1(user.salt + decoded_pass).hexdigest()
	if crypt != user.password:
		return error

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

	return request.formatter({
		'error': {
			'code': 0,
			'message': 'Not implemented'
		}
	}, error = True), 501

class ResponseHelper:

	@staticmethod
	def responsize_json(ret, error = False, version = "1.8.0"):
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
		return '<?xml version="1.0" encoding="UTF-8" ?>' + ResponseHelper.jsonp2xml({'subsonic-response': ret}).replace("&", "\\&amp;")

	@staticmethod
	def jsonp2xml(json, indent = 0):
		"""Convert a json structure to xml. The game is trivial. Nesting uses the [] parenthesis.
		  ex.  { 'musicFolder': {'id': 1234, 'name': "sss" } }
			ex. { 'musicFolder': [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }]}
			ex. { 'musicFolders': {'musicFolder' : [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }] } }
			ex. { 'index': [{'name': 'A',  'artist': [{'id': '517674445', 'name': 'Antonello Venditti'}] }] }
			ex. {"subsonic-response": { "musicFolders": {"musicFolder": [{ "id": 0,"name": "Music"}]},
	  "status": "ok","version": "1.7.0","xmlns": "http://subsonic.org/restapi"}}
				"""

		ret = '\n' + '\t' * indent
		content = None
		for c in [str, int, unicode]:
			if isinstance(json, c):
				return str(json)
		if not isinstance(json, dict):
			raise Exception("class type: %s" % json)

		# every tag is a dict.
		#	its value can be a string, a list or a dict
		for tag in json.keys():
			tag_list = json[tag]

			# if tag_list is a list, then it represent a list of elements
			#   ex. {index: [{ 'a':'1'} , {'a':'2'} ] }
			#	   --> <index a="1" /> <index b="2" />
			if isinstance(tag_list, list):
				for t in tag_list:
					# for every element, get the attributes
					#   and embed them in the tag named
					attributes = ""
					content = ""
					for (attr, value) in t.iteritems():
						# only serializable values are attributes
						if value.__class__.__name__ in 'str':
							attributes = '%s %s="%s"' % (
								attributes,
								attr,
								cgi.escape(value, quote=None)
							)
						elif value.__class__.__name__ in ['int', 'unicode', 'bool', 'long']:
							attributes = '%s %s="%s"' % (
								attributes, attr, value)
						# other values are content
						elif isinstance(value, dict):
							content += ResponseHelper.jsonp2xml(value, indent + 1)
						elif isinstance(value, list):
							content += ResponseHelper.jsonp2xml({attr: value}, indent + 1)
					if content:
						ret += "<%s%s>%s\n%s</%s>" % (
							tag, attributes, content, '\t' * indent, tag)
					else:
						ret += "<%s%s />" % (tag, attributes)
			if isinstance(tag_list, dict):
				attributes = ""
				content = ""

				for (attr, value) in tag_list.iteritems():
					# only string values are attributes
					if not isinstance(value, dict) and not isinstance(value, list):
						attributes = '%s %s="%s"' % (
							attributes, attr, value)
					else:
						content += ResponseHelper.jsonp2xml({attr: value}, indent + 1)
				if content:
					ret += "<%s%s>%s\n%s</%s>" % (tag, attributes, content, '\t' * indent, tag)
				else:
					ret += "<%s%s />" % (tag, attributes)

		return ret.replace('"True"', '"true"').replace('"False"', '"false"')

def hexdecode(enc):
	ret = ''
	while enc:
		ret = ret + chr(int(enc[:2], 16))
		enc = enc[2:]
	return ret


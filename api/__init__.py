# coding: utf-8

from flask import request
import simplejson
import cgi
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


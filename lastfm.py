# coding: utf-8

import requests, hashlib
import config
from db import session

class LastFm:
	def __init__(self, user, logger):
		self.__user = user
		self.__api_key = config.get('lastfm', 'api_key')
		self.__api_secret = config.get('lastfm', 'secret')
		self.__enabled = self.__api_key is not None and self.__api_secret is not None
		self.__logger = logger

	def link_account(self, token):
		if not self.__enabled:
			return False, 'No API key set'

		res = self.__api_request(False, method = 'auth.getSession', token = token)
		if 'error' in res:
			return False, 'Error %i: %s' % (res['error'], res['message'])
		else:
			self.__user.lastfm_session = res['session']['key']
			self.__user.lastfm_status = True
			session.commit()
			return True, 'OK'

	def unlink_account(self):
		self.__user.lastfm_session = None
		self.__user.lastfm_status = True
		session.commit()

	def now_playing(self, track):
		if not self.__enabled:
			return

		res = self.__api_request(True, method = 'track.updateNowPlaying', artist = track.album.artist.name, track = track.title, album = track.album.name,
			trackNumber = track.number, duration = track.duration)

	def scrobble(self, track, ts):
		if not self.__enabled:
			return

		res = self.__api_request(True, method = 'track.scrobble', artist = track.album.artist.name, track = track.title, album = track.album.name,
			timestamp = ts, trackNumber = track.number, duration = track.duration)

	def __api_request(self, write, **kwargs):
		if not self.__enabled:
			return

		if write:
			if not self.__user.lastfm_session or not self.__user.lastfm_status:
				return
			kwargs['sk'] = self.__user.lastfm_session

		kwargs['api_key'] = self.__api_key

		sig_str = ''
		for k, v in sorted(kwargs.iteritems()):
			if type(v) is unicode:
				sig_str += k + v.encode('utf-8')
			else:
				sig_str += k + str(v)
		sig = hashlib.md5(sig_str + self.__api_secret).hexdigest()

		kwargs['api_sig'] = sig
		kwargs['format'] = 'json'

		if write:
			r = requests.post('http://ws.audioscrobbler.com/2.0/', data = kwargs)
		else:
			r = requests.get('http://ws.audioscrobbler.com/2.0/', params = kwargs)

		if 'error' in r.json:
			if r.json['error'] in (9, '9'):
				self.__user.lastfm_status = False
				session.commit()
			self.__logger.warn('LastFM error %i: %s' % (r.json['error'], r.json['message']))

		return r.json


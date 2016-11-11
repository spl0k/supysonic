# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import string, random, hashlib
import uuid

from supysonic.db import User

class UserManager:
	SUCCESS = 0
	INVALID_ID = 1
	NO_SUCH_USER = 2
	NAME_EXISTS = 3
	WRONG_PASS = 4

	@staticmethod
	def get(store, uid):
		if type(uid) in (str, unicode):
			try:
				uid = uuid.UUID(uid)
			except:
				return UserManager.INVALID_ID, None
		elif type(uid) is uuid.UUID:
			pass
		else:
			return UserManager.INVALID_ID, None

		user = store.get(User, uid)
		if user is None:
			return UserManager.NO_SUCH_USER, None

		return UserManager.SUCCESS, user

	@staticmethod
	def add(store, name, password, mail, admin):
		if store.find(User, User.name == name).one():
			return UserManager.NAME_EXISTS

		password = UserManager.__decode_password(password)
		crypt, salt = UserManager.__encrypt_password(password)

		user = User()
		user.name = name
		user.mail = mail
		user.password = crypt
		user.salt = salt
		user.admin = admin

		store.add(user)
		store.commit()

		return UserManager.SUCCESS

	@staticmethod
	def delete(store, uid):
		status, user = UserManager.get(store, uid)
		if status != UserManager.SUCCESS:
			return status

		store.find(StarredFolder, StarredFolder.user_id == uid).remove()
		store.find(StarredArtist, StarredArtist.user_id == uid).remove()
		store.find(StarredAlbum,  StarredAlbum.user_id  == uid).remove()
		store.find(StarredTrack,  StarredTrack.user_id  == uid).remove()
		store.find(RatingFolder, RatingFolder.user_id == uid).remove()
		store.find(RatingTrack,  RatingTrack.user_id  == uid).remove()
		store.find(ChatMessage, ChatMessage.user_id == uid).remove()
		for playlist in store.find(Playlist, Playlist.user_id == uid):
			playlist.tracks.clear()
			store.remove(playlist)

		store.remove(user)
		store.commit()

		return UserManager.SUCCESS

	@staticmethod
	def try_auth(store, name, password):
		password = UserManager.__decode_password(password)
		user = store.find(User, User.name == name).one()
		if not user:
			return UserManager.NO_SUCH_USER, None
		elif UserManager.__encrypt_password(password, user.salt)[0] != user.password:
			return UserManager.WRONG_PASS, None
		else:
			return UserManager.SUCCESS, user

	@staticmethod
	def change_password(store, uid, old_pass, new_pass):
		status, user = UserManager.get(store, uid)
		if status != UserManager.SUCCESS:
			return status

		old_pass = UserManager.__decode_password(old_pass)
		new_pass = UserManager.__decode_password(new_pass)

		if UserManager.__encrypt_password(old_pass, user.salt)[0] != user.password:
			return UserManager.WRONG_PASS

		user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]
		store.commit()
		return UserManager.SUCCESS

	@staticmethod
	def change_password2(store, name, new_pass):
		user = store.find(User, User.name == name).one()
		if not user:
			return UserManager.NO_SUCH_USER

		new_pass = UserManager.__decode_password(new_pass)
		user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]
		store.commit()
		return UserManager.SUCCESS

	@staticmethod
	def error_str(err):
		if err == UserManager.SUCCESS:
			return 'No error'
		elif err == UserManager.INVALID_ID:
			return 'Invalid user id'
		elif err == UserManager.NO_SUCH_USER:
			return 'No such user'
		elif err == UserManager.NAME_EXISTS:
			return 'There is already a user with that name'
		elif err == UserManager.WRONG_PASS:
			return 'Wrong password'
		else:
			return 'Unkown error'

	@staticmethod
	def __encrypt_password(password, salt = None):
		if salt is None:
			salt = ''.join(random.choice(string.printable.strip()) for i in xrange(6))
		return hashlib.sha1(salt + password).hexdigest(), salt

	@staticmethod
	def __decode_password(password):
		if not password.startswith('enc:'):
			return password

		enc = password[4:]
		ret = ''
		while enc:
			ret = ret + chr(int(enc[:2], 16))
			enc = enc[2:]
		return ret


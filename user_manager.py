# coding: utf-8

import string, random, hashlib
import uuid

from db import User, session

class UserManager:
	ADD_SUCCESS = 0
	ADD_NAME_EXISTS = 1

	DEL_SUCCESS = 0
	DEL_INVALID_ID = 1
	DEL_NO_SUCH_USER = 2

	LOGIN_SUCCESS = 0
	LOGIN_NO_SUCH_USER = 1
	LOGIN_WRONG_PASS = 2

	@staticmethod
	def add(name, password, mail, admin):
		if User.query.filter(User.name == name).first():
			return UserManager.ADD_NAME_EXISTS

		crypt, salt = UserManager.__encrypt_password(password)
		user = User(name = name, mail = mail, password = crypt, salt = salt, admin = admin)
		session.add(user)
		session.commit()

		return UserManager.ADD_SUCCESS

	@staticmethod
	def delete(uid):
		if type(uid) in (str, unicode):
			try:
				uid = uuid.UUID(uid)
			except:
				return UserManager.DEL_INVALID_ID
		elif type(uid) is uuid.UUID:
			pass
		else:
			return UserManager.DEL_INVALID_ID

		user = User.query.get(uid)
		if user is None:
			return UserManager.DEL_NO_SUCH_USER

		session.delete(user)
		session.commit()

		return UserManager.DEL_SUCCESS

	@staticmethod
	def try_auth(name, password):
		user = User.query.filter(User.name == name).first()
		if not user:
			return UserManager.LOGIN_NO_SUCH_USER, None
		elif UserManager.__encrypt_password(password, user.salt)[0] != user.password:
			return UserManager.LOGIN_WRONG_PASS, None
		else:
			return UserManager.LOGIN_SUCCESS, user

	@staticmethod
	def __encrypt_password(password, salt = None):
		if salt is None:
			salt = ''.join(random.choice(string.printable.strip()) for i in xrange(6))
		return hashlib.sha1(salt + password).hexdigest(), salt


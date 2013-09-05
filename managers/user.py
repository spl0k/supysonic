# coding: utf-8

import string, random, hashlib
import uuid

from db import User, session

class UserManager:
	SUCCESS = 0
	INVALID_ID = 1
	NO_SUCH_USER = 2
	NAME_EXISTS = 3
	WRONG_PASS = 4

	@staticmethod
	def get(uid):
		if type(uid) in (str, unicode):
			try:
				uid = uuid.UUID(uid)
			except:
				return UserManager.INVALID_ID, None
		elif type(uid) is uuid.UUID:
			pass
		else:
			return UserManager.INVALID_ID, None

		user = User.query.get(uid)
		if user is None:
			return UserManager.NO_SUCH_USER, None

		return UserManager.SUCCESS, user

	@staticmethod
	def add(name, password, mail, admin):
		if User.query.filter(User.name == name).first():
			return UserManager.NAME_EXISTS

		password = UserManager.__decode_password(password)
		crypt, salt = UserManager.__encrypt_password(password)
		user = User(name = name, mail = mail, password = crypt, salt = salt, admin = admin)
		session.add(user)
		session.commit()

		return UserManager.SUCCESS

	@staticmethod
	def delete(uid):
		status, user = UserManager.get(uid)
		if status != UserManager.SUCCESS:
			return status

		session.delete(user)
		session.commit()

		return UserManager.SUCCESS

	@staticmethod
	def try_auth(name, password):
		password = UserManager.__decode_password(password)
		user = User.query.filter(User.name == name).first()
		if not user:
			return UserManager.NO_SUCH_USER, None
		elif UserManager.__encrypt_password(password, user.salt)[0] != user.password:
			return UserManager.WRONG_PASS, None
		else:
			return UserManager.SUCCESS, user

	@staticmethod
	def change_password(uid, old_pass, new_pass):
		status, user = UserManager.get(uid)
		if status != UserManager.SUCCESS:
			return status

		old_pass = UserManager.__decode_password(old_pass)
		new_pass = UserManager.__decode_password(new_pass)

		if UserManager.__encrypt_password(old_pass, user.salt)[0] != user.password:
			return UserManager.WRONG_PASS

		user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]
		session.commit()
		return UserManager.SUCCESS

	@staticmethod
	def change_password2(name, new_pass):
		user = User.query.filter(User.name == name).first()
		if not user:
			return UserManager.NO_SUCH_USER

		new_pass = UserManager.__decode_password(new_pass)
		user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]
		session.commit()
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


# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import hashlib
import random
import string
import uuid

from pony.orm import ObjectNotFound

from ..db import User
from ..py23 import strtype

class UserManager:
    @staticmethod
    def get(uid):
        if isinstance(uid, uuid.UUID):
            pass
        elif isinstance(uid, strtype):
            uid = uuid.UUID(uid)
        else:
            raise ValueError('Invalid user id')

        return User[uid]

    @staticmethod
    def add(name, password, mail, admin):
        if User.exists(name = name):
            raise ValueError("User '{}' exists".format(name))

        crypt, salt = UserManager.__encrypt_password(password)

        user = User(
            name = name,
            mail = mail,
            password = crypt,
            salt = salt,
            admin = admin
        )

        return user

    @staticmethod
    def delete(uid):
        user = UserManager.get(uid)
        user.delete()

    @staticmethod
    def delete_by_name(name):
        user = User.get(name = name)
        if user is None:
            raise ObjectNotFound(User)
        user.delete()

    @staticmethod
    def try_auth(name, password):
        user = User.get(name = name)
        if user is None:
            return None
        elif UserManager.__encrypt_password(password, user.salt)[0] != user.password:
            return None
        else:
            return user

    @staticmethod
    def change_password(uid, old_pass, new_pass):
        user = UserManager.get(uid)
        if UserManager.__encrypt_password(old_pass, user.salt)[0] != user.password:
            raise ValueError('Wrong password')

        user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]

    @staticmethod
    def change_password2(name, new_pass):
        user = User.get(name = name)
        if user is None:
            raise ObjectNotFound(User)

        user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]

    @staticmethod
    def __encrypt_password(password, salt = None):
        if salt is None:
            salt = ''.join(random.choice(string.printable.strip()) for _ in range(6))
        return hashlib.sha1(salt.encode('utf-8') + password.encode('utf-8')).hexdigest(), salt


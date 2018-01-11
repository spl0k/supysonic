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

from pony.orm import db_session
from pony.orm import ObjectNotFound

from ..db import User, ChatMessage, Playlist
from ..db import StarredFolder, StarredArtist, StarredAlbum, StarredTrack
from ..db import RatingFolder, RatingTrack
from ..py23 import strtype

class UserManager:
    SUCCESS = 0
    INVALID_ID = 1
    NO_SUCH_USER = 2
    NAME_EXISTS = 3
    WRONG_PASS = 4

    @staticmethod
    @db_session
    def get(uid):
        if isinstance(uid, strtype):
            try:
                uid = uuid.UUID(uid)
            except:
                return UserManager.INVALID_ID, None
        elif isinstance(uid, uuid.UUID):
            pass
        else:
            return UserManager.INVALID_ID, None

        try:
            user = User[uid]
            return UserManager.SUCCESS, user
        except ObjectNotFound:
            return UserManager.NO_SUCH_USER, None

    @staticmethod
    @db_session
    def add(name, password, mail, admin):
        if User.get(name = name) is not None:
            return UserManager.NAME_EXISTS

        crypt, salt = UserManager.__encrypt_password(password)

        user = User(
            name = name,
            mail = mail,
            password = crypt,
            salt = salt,
            admin = admin
        )

        return UserManager.SUCCESS

    @staticmethod
    @db_session
    def delete(uid):
        status, user = UserManager.get(uid)
        if status != UserManager.SUCCESS:
            return status

        user.delete()
        return UserManager.SUCCESS

    @staticmethod
    @db_session
    def delete_by_name(name):
        user = User.get(name = name)
        if user is None:
            return UserManager.NO_SUCH_USER
        return UserManager.delete(user.id)

    @staticmethod
    @db_session
    def try_auth(name, password):
        user = User.get(name = name)
        if user is None:
            return UserManager.NO_SUCH_USER, None
        elif UserManager.__encrypt_password(password, user.salt)[0] != user.password:
            return UserManager.WRONG_PASS, None
        else:
            return UserManager.SUCCESS, user

    @staticmethod
    @db_session
    def change_password(uid, old_pass, new_pass):
        status, user = UserManager.get(uid)
        if status != UserManager.SUCCESS:
            return status

        if UserManager.__encrypt_password(old_pass, user.salt)[0] != user.password:
            return UserManager.WRONG_PASS

        user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]
        return UserManager.SUCCESS

    @staticmethod
    @db_session
    def change_password2(name, new_pass):
        user = User.get(name = name)
        if user is None:
            return UserManager.NO_SUCH_USER

        user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]
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
            salt = ''.join(random.choice(string.printable.strip()) for _ in range(6))
        return hashlib.sha1(salt.encode('utf-8') + password.encode('utf-8')).hexdigest(), salt


# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2017 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import binascii
import string
import random
import hashlib
import uuid

from supysonic.db import User, ChatMessage, Playlist
from supysonic.db import StarredFolder, StarredArtist, StarredAlbum, StarredTrack
from supysonic.db import RatingFolder, RatingTrack

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

        store.find(StarredFolder, StarredFolder.user_id == user.id).remove()
        store.find(StarredArtist, StarredArtist.user_id == user.id).remove()
        store.find(StarredAlbum,  StarredAlbum.user_id  == user.id).remove()
        store.find(StarredTrack,  StarredTrack.user_id  == user.id).remove()
        store.find(RatingFolder, RatingFolder.user_id == user.id).remove()
        store.find(RatingTrack,  RatingTrack.user_id  == user.id).remove()
        store.find(ChatMessage, ChatMessage.user_id == user.id).remove()
        for playlist in store.find(Playlist, Playlist.user_id == user.id):
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
        return hashlib.sha1(salt.encode('utf-8') + password.encode('utf-8')).hexdigest(), salt

    @staticmethod
    def __decode_password(password):
        if not password.startswith('enc:'):
            return password

        try:
            return binascii.unhexlify(password[4:]).decode('utf-8')
        except:
            return password

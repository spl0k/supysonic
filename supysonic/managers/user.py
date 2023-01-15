# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import hashlib
import random
import string
import uuid

from ..db import User


class UserManager:
    @staticmethod
    def get(uid):
        if isinstance(uid, uuid.UUID):
            pass
        elif isinstance(uid, str):
            uid = uuid.UUID(uid)
        else:
            raise TypeError("Invalid user id")

        return User[uid]

    @staticmethod
    def add(name, password, **kwargs):
        if User.select().where(User.name == name).exists():
            raise ValueError(f"User '{name}' exists")

        crypt, salt = UserManager.__encrypt_password(password)
        return User.create(name=name, password=crypt, salt=salt, **kwargs)

    @staticmethod
    def delete(uid):
        user = UserManager.get(uid)
        user.delete_instance(recursive=True)

    @staticmethod
    def delete_by_name(name):
        user = User.get(name=name)
        user.delete_instance(recursive=True)

    @staticmethod
    def try_auth(name, password):
        user = User.get_or_none(name=name)
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
            raise ValueError("Wrong password")

        user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]
        user.save()

    @staticmethod
    def change_password2(name_or_user, new_pass):
        if isinstance(name_or_user, User):
            user = name_or_user
        elif isinstance(name_or_user, str):
            user = User.get(name=name_or_user)
        else:
            raise TypeError("Requires a User instance or a user name (string)")

        user.password = UserManager.__encrypt_password(new_pass, user.salt)[0]
        user.save()

    @staticmethod
    def __encrypt_password(password, salt=None):
        if salt is None:
            salt = "".join(random.choice(string.printable.strip()) for _ in range(6))
        return (
            hashlib.sha1(salt.encode("utf-8") + password.encode("utf-8")).hexdigest(),
            salt,
        )

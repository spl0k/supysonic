# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import hashlib
import hmac
import logging
import random
import string
import uuid

from werkzeug.security import check_password_hash, generate_password_hash

from ..db import User

_PASSWORD_SEPARATOR = "#"

logger = logging.getLogger(__name__)


def _generate_random_string(length):
    return "".join(random.choice(string.printable.strip()) for _ in range(length))


_DUMMY_HASH = generate_password_hash(_generate_random_string(20))


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

        return User.create(
            name=name, password=generate_password_hash(password), **kwargs
        )

    @staticmethod
    def delete(uid):
        user = UserManager.get(uid)
        user.delete_instance(recursive=True)

    @staticmethod
    def delete_by_name(name):
        user = User.get(name=name)
        user.delete_instance(recursive=True)

    @staticmethod
    def __compare_password(user, password):
        if _PASSWORD_SEPARATOR in user.password:
            salt = user.password.partition(_PASSWORD_SEPARATOR)[2]
            encrypted = UserManager.__legacy_password_hash(password, salt)
            return hmac.compare_digest(encrypted, user.password)
        else:
            return check_password_hash(user.password, password)

    @staticmethod
    def try_auth(name, password):
        user = User.get_or_none(name=name)
        if user is None:
            # Compare against a dummy hash to prevent user enumeration through
            # timing attacks
            check_password_hash(_DUMMY_HASH, password)
            return None

        if UserManager.__compare_password(user, password):
            # Updgrade hash if needed
            if _PASSWORD_SEPARATOR in user.password:
                user.password = generate_password_hash(password)
                user.save()
                logger.info("Upgraded password hash for user %s", user.name)

            return user

        return None

    @staticmethod
    def change_password(uid, old_pass, new_pass):
        user = UserManager.get(uid)
        if not UserManager.__compare_password(user, old_pass):
            raise ValueError("Wrong password")

        user.password = generate_password_hash(new_pass)
        user.save()

    @staticmethod
    def change_password2(name_or_user, new_pass):
        if isinstance(name_or_user, User):
            user = name_or_user
        elif isinstance(name_or_user, str):
            user = User.get(name=name_or_user)
        else:
            raise TypeError("Requires a User instance or a user name (string)")

        user.password = generate_password_hash(new_pass)
        user.save()

    @staticmethod
    def __legacy_password_hash(password, salt=None):
        if salt is None:
            salt = _generate_random_string(6)
        digest = hashlib.sha1(salt.encode() + password.encode()).hexdigest()
        return f"{digest}{_PASSWORD_SEPARATOR}{salt}"

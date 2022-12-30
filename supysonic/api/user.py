# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request
from functools import wraps

from ..db import User
from ..managers.user import UserManager

from . import decode_password, api_routing
from .exceptions import Forbidden


def admin_only(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.user.admin:
            raise Forbidden()
        return f(*args, **kwargs)

    return decorated


@api_routing("/getUser")
def user_info():
    username = request.values["username"]

    if username != request.user.name and not request.user.admin:
        raise Forbidden()

    user = User.get(name=username)
    return request.formatter("user", user.as_subsonic_user())


@api_routing("/getUsers")
@admin_only
def users_info():
    return request.formatter(
        "users", {"user": [u.as_subsonic_user() for u in User.select()]}
    )


def get_roles_dict():
    roles = {}
    for role in ("admin", "jukebox"):
        value = request.values.get(role + "Role")
        value = value in (True, "True", "true", 1, "1")
        roles[role] = value

    return roles


@api_routing("/createUser")
@admin_only
def user_add():
    username = request.values["username"]
    password = request.values["password"]
    email = request.values["email"]
    roles = get_roles_dict()

    password = decode_password(password)
    UserManager.add(username, password, mail=email, **roles)

    return request.formatter.empty


@api_routing("/deleteUser")
@admin_only
def user_del():
    username = request.values["username"]
    UserManager.delete_by_name(username)

    return request.formatter.empty


@api_routing("/changePassword")
def user_changepass():
    username = request.values["username"]
    password = request.values["password"]

    if username != request.user.name and not request.user.admin:
        raise Forbidden()

    password = decode_password(password)
    UserManager.change_password2(username, password)

    return request.formatter.empty


@api_routing("/updateUser")
@admin_only
def user_edit():
    username = request.values["username"]
    user = User.get(name=username)

    if "password" in request.values:
        password = decode_password(request.values["password"])
        UserManager.change_password2(user, password)

    email, admin, jukebox = map(
        request.values.get, ("email", "adminRole", "jukeboxRole")
    )
    if email is not None:
        user.mail = email

    if admin is not None:
        admin = admin in (True, "True", "true", 1, "1")
        user.admin = admin

    if jukebox is not None:
        jukebox = jukebox in (True, "True", "true", 1, "1")
        user.jukebox = jukebox

    user.save()

    return request.formatter.empty

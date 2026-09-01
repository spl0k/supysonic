# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from ..app.flask import app_layer
from ..db import User
from ._blueprint import api_routing
from ._exceptions import Forbidden
from ._helpers import admin_only, decode_password, get_bool, get_mail


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
    return {role: get_bool(role + "Role", False) for role in ("admin", "jukebox")}


@api_routing("/createUser")
@admin_only
def user_add():
    username = request.values["username"]
    password = request.values["password"]
    email = get_mail("email")
    roles = get_roles_dict()

    password = decode_password(password)
    app_layer.users.add(username, password, mail=email, **roles)

    return request.formatter.empty


@api_routing("/deleteUser")
@admin_only
def user_del():
    username = request.values["username"]
    app_layer.users.delete_by_name(username)

    return request.formatter.empty


@api_routing("/changePassword")
def user_changepass():
    username = request.values["username"]
    password = request.values["password"]

    if username != request.user.name and not request.user.admin:
        raise Forbidden()

    password = decode_password(password)
    app_layer.users.change_password2(username, password)

    return request.formatter.empty


@api_routing("/updateUser")
@admin_only
def user_edit():
    username = request.values["username"]
    user = User.get(name=username)

    if "password" in request.values:
        password = decode_password(request.values["password"])
        app_layer.users.change_password2(user, password)

    admin = get_bool("adminRole")
    jukebox = get_bool("jukeboxRole")

    if "email" in request.values:
        user.mail = get_mail("email")

    if admin is not None:
        user.admin = admin

    if jukebox is not None:
        user.jukebox = jukebox

    user.save()

    return request.formatter.empty

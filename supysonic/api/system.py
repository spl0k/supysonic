# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from . import api


@api.route("/ping.view", methods=["GET", "POST"])
def ping():
    return request.formatter.empty


@api.route("/getLicense.view", methods=["GET", "POST"])
def license():
    return request.formatter("license", dict(valid=True))

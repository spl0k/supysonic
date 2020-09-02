# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2020 Óscar García Amor <ogarcia@connectical.com>
#
# Distributed under terms of the GNU GPLv3 license.

from flask import request

from . import api

@api.route("/getVideos.view", methods=["GET", "POST"])
def get_videos():
    return request.formatter(
            "videos",
            dict(video=[])
    )

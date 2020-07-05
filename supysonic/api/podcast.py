# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import request

from ..db import PodcastChannel, PodcastEpisode

from . import api, get_entity, require_podcast
from .exceptions import Forbidden, MissingParameter, NotFound


@api.route("/getPodcasts.view", methods=["GET", "POST"])
def get_podcasts():
    include_episodes, channel_id = map(request.values.get, ["includeEpisodes", "id"])

    if channel_id:
        channels = (get_entity(PodcastChannel),)
    else:
        channels = PodcastChannel.select().sort_by(PodcastChannel.url)

    return request.formatter(
        "podcasts",
        dict(channel=[ch.as_subsonic_channel(include_episodes) for ch in channels]),
    )


@api.route("/createPodcastChannel.view", methods=["GET", "POST"])
@require_podcast
def create_podcast_channel():
    url = request.values["url"]

    PodcastChannel(url=url)

    return request.formatter.empty


@api.route("/deletePodcastChannel.view", methods=["GET", "POST"])
@require_podcast
def delete_podcast_channel():
    res = get_entity(PodcastChannel)
    res.delete()

    return request.formatter.empty


@api.route("/deletePodcastEpisode.view", methods=["GET", "POST"])
@require_podcast
def delete_podcast_episode():
    res = get_entity(PodcastEpisode)
    res.delete()

    return request.formatter.empty



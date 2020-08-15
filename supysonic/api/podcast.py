# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
from datetime import datetime
from time import mktime
from urllib.parse import urlparse

from flask import request
import feedparser

from ..db import PodcastChannel, PodcastEpisode, PodcastStatus

from . import api, get_entity, require_podcast
from .exceptions import Forbidden, MissingParameter, NotFound


@api.route("/getPodcasts.view", methods=["GET", "POST"])
def get_podcasts():
    include_episodes, channel_id = map(request.values.get, ["includeEpisodes", "id"])

    if channel_id:
        channels = (get_entity(PodcastChannel),)
    else:
        channels = PodcastChannel \
            .select(lambda chan: chan.status != PodcastStatus.deleted.value) \
            .sort_by(PodcastChannel.url)

    return request.formatter(
        "podcasts",
        dict(channel=[ch.as_subsonic_channel(include_episodes) for ch in channels]),
    )


@api.route("/createPodcastChannel.view", methods=["GET", "POST"])
@require_podcast
def create_podcast_channel():
    url = request.values["url"]
    parsed_url = urlparse(url)
    has_scheme_and_location = parsed_url.scheme and (parsed_url.netloc or parsed_url.path)
    if not has_scheme_and_location:
        return request.formatter.error(10, 'unexepected url')

    feed = feedparser.parse(url)
    channel = PodcastChannel(
        url=url,
        title=feed.feed.title,
    )

    for item in feed.entries:
        channel.episodes.create(
            title=item.title,
            description=item.description,
            stream_url=item.links[0].href,
            duration=item.links[0].length,
            publish_date=datetime.fromtimestamp(mktime(item.published_parsed)),
            status=PodcastStatus.new.value,
        )

    return request.formatter.empty


@api.route("/deletePodcastChannel.view", methods=["GET", "POST"])
@require_podcast
def delete_podcast_channel():
    res = get_entity(PodcastChannel)
    res.soft_delete()

    return request.formatter.empty


@api.route("/deletePodcastEpisode.view", methods=["GET", "POST"])
@require_podcast
def delete_podcast_episode():
    res = get_entity(PodcastEpisode)
    res.soft_delete()

    return request.formatter.empty


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


def fetch_feed(url):
    parsed_url = urlparse(url)

    has_scheme_and_location = parsed_url.scheme and (parsed_url.netloc or parsed_url.path)
    if not has_scheme_and_location:
        return None, request.formatter.error(10, 'unexepected url')

    try:
        feed = feedparser.parse(url)
    except Exception as ex:
        return None, request.formatter.error(0, 'unexpected error')

    if feed.status != 200:
        return None, request.formatter.error(0, 'http:' + feed.status)

    if feed.bozo:
        return None, request.formatter.error(0, feed.bozo_exception)

    if not hasattr(feed.feed, 'title'):
        return None, request.formatter.error(10, 'title missing')

    return feed, None


@api.route("/createPodcastChannel.view", methods=["GET", "POST"])
@require_podcast
def create_podcast_channel():
    url = request.values["url"]
    feed, error = fetch_feed(url)
    if error:
        return error

    channel = PodcastChannel(
        url=url,
        title=feed.feed.title,
    )

    for item in feed.entries:
        # NOTE: 'suffix' and 'bitrate' will be set when downloading to local file

        fields = {
            'title': item.title,
            'description': item['description'],
            'year': item.published_parsed.tm_year,
            'publish_date': datetime.fromtimestamp(mktime(item.published_parsed)),
            'status': PodcastStatus.new.value,
        }

        audio_link = next((link for link in item.links if link.type == 'audio/mpeg'), None)
        if audio_link:
            fields['stream_url'] = audio_link.href
            fields['size'] = audio_link.length
            fields['content_type'] = audio_link.type
        else:
            fields['status'] = PodcastStatus.error.value
            fields['error_message'] = 'Audio link not found in episode xml'

        if item['itunes_duration']:
            fields['duration'] = item.itunes_duration

        if feed.feed['image'] and feed.feed.image['href']:
            fields['cover_art'] = feed.feed.image.href

        if feed.feed['tags']:
            fields['genre'] = ",".join([tag['term'] for tag in feed.feed.tags])

        channel.episodes.create(**fields)

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


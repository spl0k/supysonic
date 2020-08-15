#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import os
import uuid

from pony.orm import db_session

from supysonic.db import PodcastChannel, PodcastEpisode, PodcastStatus

from unittest import skip

from .apitestbase import ApiTestBase


class PodcastTestCase(ApiTestBase):
    _non_admin_user_ = {"u": "bob", "p": "B0b", "username": "alice"}

    def setUp(self):
        super(PodcastTestCase, self).setUp()

    @db_session
    def assertDbCountEqual(self, entity, count):
        self.assertEqual(entity.select().count(), count)

    def assertPodcastChannelEquals(self, channel, url, status, title=None, description=None, error_message=None):
        self.assertEqual(channel.url, url)
        self.assertEqual(channel.status, status)
        if title:
            self.assertEqual(channel.title, title)
        if description:
            self.assertEqual(channel.description, description)
        self.assertEqual(channel.error_message, error_message)

    def test_create_podcast_channel(self):
        # test for non-admin access
        self._make_request(
            "createPodcastChannel",
            self._non_admin_user_,
            error=50
        )

        # check params
        self._make_request("createPodcastChannel", error=10)
        self._make_request("createPodcastChannel", {"url": "bad url"}, error=10)

        # create w/ required fields
        url = "file://" + os.path.join(os.path.dirname(__file__), "../fixtures/rssfeed.xml")
        self._make_request("createPodcastChannel", {"url": url}, skip_post=True)

        self.assertDbCountEqual(PodcastChannel, 1)
        self.assertDbCountEqual(PodcastEpisode, 20)

        with db_session:
            self.assertPodcastChannelEquals(PodcastChannel.select().first(), url, PodcastStatus.new.value)
            for episode in PodcastEpisode.select():
                self.assertEqual(episode.status, PodcastStatus.new.value)


    def test_delete_podcast_channel(self):
        # test for non-admin access
        self._make_request(
            "deletePodcastChannel",
            self._non_admin_user_,
            error=50
        )

        # check params
        self._make_request("deletePodcastChannel", error=10)
        self._make_request("deletePodcastChannel", {"id": 1}, error=0)
        self._make_request("deletePodcastChannel", {"id": str(uuid.uuid4())}, error=70)

        # delete
        with db_session:
            channel = PodcastChannel(
                url="https://example.local/podcast/delete",
                status=PodcastStatus.new.value,
            )

        self._make_request("deletePodcastChannel", {"id": channel.id}, skip_post=True)

        self.assertDbCountEqual(PodcastChannel, 1)

        with db_session:
            self.assertEqual(PodcastStatus.deleted.value, PodcastChannel[channel.id].status)

    @db_session
    def test_delete_podcast_episode(self):
        # test for non-admin access
        self._make_request(
            "deletePodcastEpisode",
            self._non_admin_user_,
            error=50
        )

        # check params
        self._make_request("deletePodcastEpisode", error=10)
        self._make_request("deletePodcastEpisode", {"id": 1}, error=0)
        self._make_request("deletePodcastEpisode", {"id": str(uuid.uuid4())}, error=70)

        # delete
        channel = PodcastChannel(
            url="https://example.local/episode/delete",
            status=PodcastStatus.new.value,
        )
        episode = channel.episodes.create(
            title="Test Episode 1",
            stream_url="https://supysonic.local/delete/1",
            status=PodcastStatus.new.value,
        )
        channel.episodes.create(
            title="Test Episode 2",
            stream_url="https://supysonic.local/delete/2",
            status=PodcastStatus.new.value,
        )

        # validate starting condition
        self.assertDbCountEqual(PodcastEpisode, 2)

        # validate delete of an episode
        self._make_request("deletePodcastEpisode", {"id": episode.id}, skip_post=True)
        ## marked as deleted
        self.assertDbCountEqual(PodcastEpisode, 2)
        self.assertEqual(PodcastStatus.deleted.value, PodcastEpisode[episode.id].status)

        # test for cascading delete on PodcastChannel
        self._make_request("deletePodcastChannel", {"id": channel.id}, skip_post=True)
        ## counts are the same but the status is now "deleted"
        self.assertDbCountEqual(PodcastChannel, 1)
        self.assertEqual(PodcastStatus.deleted.value, PodcastChannel[channel.id].status)
        self.assertDbCountEqual(PodcastEpisode, 2)
        for ep in PodcastEpisode.select():
            self.assertEqual(PodcastStatus.deleted.value, ep.status)

    def test_get_podcasts(self):
        test_range = 3
        with db_session:
            for x in range(test_range):
                ch = PodcastChannel(
                    url="https://example.local/podcast-{}".format(x),
                    status=PodcastStatus.new.value,
                )
                for y in range(x + 1):
                    ch.episodes.create(
                        title="episode {} for channel {}".format(y, x),
                        stream_url="https://supysonic.local/get/{}/{}".format(x, y),
                    )

        # verify data is stored
        self.assertDbCountEqual(PodcastChannel, test_range)

        # compare api response to inventory
        rv, channels = self._make_request("getPodcasts", tag="podcasts")
        self.assertEqual(len(channels), test_range)

        # This order is guaranteed to work because the api returns in order by name.
        # Test data is sequential by design.
        for x in range(test_range):
            channel = channels[x]
            self.assertTrue(channel.get("url").endswith("podcast-{}".format(x)))
            self.assertEqual(channel.get("status"), "new")

        # test for non-admin access
        rv, channels = self._make_request(
            "getPodcasts",
            self._non_admin_user_,
            tag="podcasts",
        )
        self.assertEqual(len(channels), test_range)

        # test retrieving a podcast by id
        for channel in channels:
            rv, test_channels = self._make_request("getPodcasts", {"id": channel.get("id"), "includeEpisodes": True}, tag="podcasts", skip_post=True)
            # expect to work with only 1
            self.assertEqual(len(test_channels), 1)
            test_channel = test_channels[0]
            self.assertEqual(test_channel.get("id"), channel.get("id"))

            # should have as many episodes as noted in the url
            count = int(channel.get("url")[-1]) + 1
            self.assertEqual(len(test_channel), count)

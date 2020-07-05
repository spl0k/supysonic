#!/usr/bin/env python
# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from pony.orm import db_session

from supysonic.db import PodcastChannel, PodcastEpisode

from unittest import skip

from .apitestbase import ApiTestBase


class PodcastTestCase(ApiTestBase):
    _non_admin_user_ = {"u": "bob", "p": "B0b", "username": "alice"}

    def setUp(self):
        super(PodcastTestCase, self).setUp()

    @db_session
    def assertDbCountEqual(self, entity, count):
        self.assertEqual(entity.select().count(), count)

    def assertPodcastChannelEquals(self, channel, url, status, title='', description='', error_message=''):
        self.assertEqual(channel.url, url)
        self.assertEqual(channel.title, title)
        self.assertEqual(channel.description, description)
        self.assertEqual(channel.status, status)
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

        # create w/ required fields
        url = "https://example.local/podcast_channel/create"

        self._make_request("createPodcastChannel", {"url": url})

        # the correct value is 2 because _make_request uses GET then POST
        self.assertDbCountEqual(PodcastChannel, 2)

        with db_session:
            for channel in PodcastChannel.select():
                self.assertPodcastChannelEquals(channel, url, "new")


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
                status="new",
            )

        self._make_request("deletePodcastChannel", {"id": channel.id}, skip_post=True)

        self.assertDbCountEqual(PodcastChannel, 0)

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
        with db_session:
            channel = PodcastChannel(
                url="https://example.local/episode/delete",
                status="new",
            )
            episode = channel.episodes.create(
                description="Test Episode 1",
                status="new",
            )
            channel.episodes.create(
                description="Test Episode 2",
                status="new",
            )

        # validate starting condition
        self.assertDbCountEqual(PodcastEpisode, 2)

        # validate delete of an episode
        self._make_request("deletePodcastEpisode", {"id": episode.id}, skip_post=True)
        self.assertDbCountEqual(PodcastEpisode, 1)

        # test for cascading delete on PodcastChannel
        self._make_request("deletePodcastChannel", {"id": channel.id}, skip_post=True)
        self.assertDbCountEqual(PodcastChannel, 0)
        self.assertDbCountEqual(PodcastEpisode, 0)

    def test_get_podcasts(self):
        test_range = 3
        with db_session:
            for x in range(test_range):
                ch = PodcastChannel(
                    url="https://example.local/podcast-{}".format(x),
                    status="new",
                )
                for y in range(x + 1):
                    ch.episodes.create(description="episode {} for channel {}".format(y, x))

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
            self.assertTrue(channel.get("status").endswith("new"))

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

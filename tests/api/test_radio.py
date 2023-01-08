# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2020-2022 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import uuid

from supysonic.db import RadioStation

from .apitestbase import ApiTestBase


class RadioStationTestCase(ApiTestBase):
    def assertRadioStationCountEqual(self, count):
        self.assertEqual(RadioStation.select().count(), count)

    def assertRadioStationEquals(self, station, stream_url, name, homepage_url=None):
        self.assertEqual(station.stream_url, stream_url)
        self.assertEqual(station.name, name)
        self.assertEqual(station.homepage_url, homepage_url)

    def test_create_radio_station(self):
        # test for non-admin access
        self._make_request(
            "createInternetRadioStation",
            {"u": "bob", "p": "B0b", "username": "alice"},
            error=50,
        )

        # check params
        self._make_request("createInternetRadioStation", error=10)
        self._make_request(
            "createInternetRadioStation", {"streamUrl": "missingName"}, error=10
        )
        self._make_request(
            "createInternetRadioStation", {"name": "missing stream"}, error=10
        )

        # create w/ required fields
        stream_url = "http://example.com/radio/create"
        name = "radio station"

        self._make_request(
            "createInternetRadioStation", {"streamUrl": stream_url, "name": name}
        )

        # the correct value is 2 because _make_request uses GET then POST
        self.assertRadioStationCountEqual(2)

        for rs in RadioStation.select():
            self.assertRadioStationEquals(rs, stream_url, name)

            RadioStation.delete().execute()

        # create w/ all fields
        stream_url = "http://example.com/radio/create1"
        name = "radio station1"
        homepage_url = "http://example.com/home"

        self._make_request(
            "createInternetRadioStation",
            {"streamUrl": stream_url, "name": name, "homepageUrl": homepage_url},
        )

        # the correct value is 2 because _make_request uses GET then POST
        self.assertRadioStationCountEqual(2)

        for rs in RadioStation.select():
            self.assertRadioStationEquals(rs, stream_url, name, homepage_url)

    def test_update_radio_station(self):
        self._make_request(
            "updateInternetRadioStation",
            {"u": "bob", "p": "B0b", "username": "alice"},
            error=50,
        )

        # test data
        test = {
            "stream_url": "http://example.com/radio/update",
            "name": "Radio Update",
            "homepage_url": "http://example.com/update",
        }
        update = {
            "stream_url": test["stream_url"] + "-1",
            "name": test["name"] + "-1",
            "homepage_url": test["homepage_url"] + "-1",
        }

        # load a test record
        station = RadioStation.create(
            stream_url=test["stream_url"],
            name=test["name"],
            homepage_url=test["homepage_url"],
        )

        # check params
        self._make_request(
            "updateInternetRadioStation",
            {"id": station.id, "homepageUrl": "missing required params"},
            error=10,
        )
        self._make_request(
            "updateInternetRadioStation",
            {"id": station.id, "name": "missing streamUrl"},
            error=10,
        )
        self._make_request(
            "updateInternetRadioStation",
            {"id": station.id, "streamUrl": "missing name"},
            error=10,
        )

        # update the record w/ required fields
        self._make_request(
            "updateInternetRadioStation",
            {
                "id": station.id,
                "streamUrl": update["stream_url"],
                "name": update["name"],
            },
        )

        rs_update = RadioStation[station.id]

        self.assertRadioStationEquals(
            rs_update, update["stream_url"], update["name"], test["homepage_url"]
        )

        # update the record w/ all fields
        self._make_request(
            "updateInternetRadioStation",
            {
                "id": station.id,
                "streamUrl": update["stream_url"],
                "name": update["name"],
                "homepageUrl": update["homepage_url"],
            },
        )

        rs_update = RadioStation[station.id]

        self.assertRadioStationEquals(
            rs_update, update["stream_url"], update["name"], update["homepage_url"]
        )

    def test_delete_radio_station(self):
        # test for non-admin access
        self._make_request(
            "deleteInternetRadioStation",
            {"u": "bob", "p": "B0b", "username": "alice"},
            error=50,
        )

        # check params
        self._make_request("deleteInternetRadioStation", error=10)
        self._make_request("deleteInternetRadioStation", {"id": 1}, error=0)
        self._make_request(
            "deleteInternetRadioStation", {"id": str(uuid.uuid4())}, error=70
        )

        # delete
        station = RadioStation.create(
            stream_url="http://example.com/radio/delete",
            name="Radio Delete",
            homepage_url="http://example.com/update",
        )

        self._make_request(
            "deleteInternetRadioStation", {"id": station.id}, skip_post=True
        )

        self.assertRadioStationCountEqual(0)

    def test_get_radio_stations(self):
        test_range = 3
        for x in range(test_range):
            RadioStation.create(
                stream_url=f"http://example.com/radio-{x}",
                name=f"Radio {x}",
                homepage_url=f"http://example.com/update-{x}",
            )

        # verify happy path is clean
        self.assertRadioStationCountEqual(test_range)
        rv, child = self._make_request(
            "getInternetRadioStations", tag="internetRadioStations"
        )
        self.assertEqual(len(child), test_range)
        # This order is guaranteed to work because the api returns in order by name.
        # Test data is sequential by design.
        for x in range(test_range):
            station = child[x]
            self.assertTrue(station.get("streamUrl").endswith(f"radio-{x}"))
            self.assertTrue(station.get("name").endswith(f"Radio {x}"))
            self.assertTrue(station.get("homePageUrl").endswith(f"update-{x}"))

        # test for non-admin access
        rv, child = self._make_request(
            "getInternetRadioStations",
            {"u": "bob", "p": "B0b", "username": "alice"},
            tag="internetRadioStations",
        )

        self.assertEqual(len(child), test_range)

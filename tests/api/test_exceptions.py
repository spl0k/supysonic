# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest

from flask import request
from lxml import etree

from supysonic.api.exceptions import (
    AggregateException,
    GenericError,
    InvalidParameter,
    MissingParameter,
    NotFound,
    SubsonicAPIException,
)
from supysonic.api.formatters import XMLFormatter

from .apitestbase import ApiTestBase

NS = "http://subsonic.org/restapi"


class ExceptionsTestCase(ApiTestBase):
    def test_str(self):
        # api_code set: "<code>: <message>"
        self.assertEqual(str(GenericError("boom")), "0: boom")
        self.assertEqual(str(NotFound("Track")), "70: Track not found")
        # api_code unset falls back to "??"
        self.assertEqual(str(SubsonicAPIException()), "??: None")

    def test_parameter_errors_name_the_parameter(self):
        self.assertEqual(
            str(InvalidParameter("size")), "0: Invalid value for parameter 'size'"
        )
        self.assertEqual(
            str(InvalidParameter("size", "not an integer")),
            "0: Invalid value for parameter 'size': not an integer",
        )
        self.assertEqual(
            str(MissingParameter("index")),
            "10: A required parameter is missing: 'index'.",
        )
        # the generic form, used when the name isn't known
        self.assertEqual(
            str(MissingParameter()), "10: A required parameter is missing."
        )

    def test_missing_parameter_name_from_request(self):
        # A bare request.values[...] lookup goes through the BadRequestKeyError
        # handler, which recovers the key name off the KeyError.
        rv = self.client.get(
            "/rest/getAlbumList.view",
            query_string={"u": "alice", "p": "Alic3", "c": "tests", "v": "1.12.0"},
        )
        xml = etree.fromstring(rv.data)
        self.assertEqual(xml[0].get("code"), "10")
        self.assertIn("type", xml[0].get("message"))

        # ... and so does a missing authentication parameter
        rv = self.client.get("/rest/ping.view", query_string={"c": "tests"})
        xml = etree.fromstring(rv.data)
        self.assertEqual(xml[0].get("code"), "10")
        self.assertIn("'u'", xml[0].get("message"))

    def __error_xml(self, exc):
        with self.request_context("/rest/star.view"):
            request.formatter = XMLFormatter()
            resp = exc.get_response()
            return etree.fromstring(resp.get_data())

    def test_aggregate_single(self):
        # A lone exception delegates to that exception's own response.
        xml = self.__error_xml(AggregateException([NotFound("Track")]))
        err = xml[0]
        self.assertEqual(err.tag, f"{{{NS}}}error")
        self.assertEqual(err.get("code"), "70")
        self.assertEqual(err.get("message"), "Track not found")

    def test_aggregate_same_code(self):
        # Several errors sharing an api_code keep that code, listing each error.
        xml = self.__error_xml(
            AggregateException([NotFound("Track"), NotFound("Album")])
        )
        err = xml[0]
        self.assertEqual(err.get("code"), "70")
        self.assertEqual(len(err), 2)

    def test_aggregate_differing_codes(self):
        # Mixed api_codes collapse to the generic code 0.
        xml = self.__error_xml(
            AggregateException([NotFound("Track"), GenericError("boom")])
        )
        err = xml[0]
        self.assertEqual(err.get("code"), "0")
        self.assertEqual(len(err), 2)
        codes = sorted(child.get("code") for child in err)
        self.assertEqual(codes, ["0", "70"])

    def test_aggregate_converts_plain_exceptions(self):
        # Plain (non-Subsonic) exceptions are routed through the API error
        # handlers: a ValueError maps to a handler, an unhandled one falls
        # back to a GenericError.
        with self.request_context("/rest/star.view"):
            request.formatter = XMLFormatter()
            exc = AggregateException([ValueError("bad value"), RuntimeError("boom")])

        self.assertEqual(len(exc.exceptions), 2)
        for converted in exc.exceptions:
            self.assertIsInstance(converted, SubsonicAPIException)
        # The ValueError handler and the fallback both yield code 0
        self.assertEqual({e.api_code for e in exc.exceptions}, {0})


if __name__ == "__main__":
    unittest.main()

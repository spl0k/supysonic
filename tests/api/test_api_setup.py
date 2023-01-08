# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2018 Alban 'spl0k' Féron
#                    2017 Óscar García Amor
#
# Distributed under terms of the GNU AGPLv3 license.

import base64
import flask.json
import unittest

from xml.etree import ElementTree

from ..testbase import TestBase
from ..utils import hexlify


class ApiSetupTestCase(TestBase):
    __with_api__ = True

    def setUp(self):
        super().setUp()
        self._patch_client()

    def __basic_auth_get(self, username, password):
        hashed = base64.b64encode(f"{username}:{password}".encode("utf-8"))
        headers = {"Authorization": "Basic " + hashed.decode("utf-8")}
        return self.client.get(
            "/rest/ping.view", headers=headers, query_string={"c": "tests"}
        )

    def __query_params_auth_get(self, username, password):
        return self.client.get(
            "/rest/ping.view", query_string={"c": "tests", "u": username, "p": password}
        )

    def __query_params_auth_enc_get(self, username, password):
        return self.__query_params_auth_get(username, "enc:" + hexlify(password))

    def __form_auth_post(self, username, password):
        return self.client.post(
            "/rest/ping.view", data={"c": "tests", "u": username, "p": password}
        )

    def __form_auth_enc_post(self, username, password):
        return self.__form_auth_post(username, "enc:" + hexlify(password))

    def __test_auth(self, method):
        # non-existent user
        rv = method("null", "null")
        self.assertEqual(rv.status_code, 200)
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="40"', rv.data)

        # user request with bad password
        rv = method("alice", "wrong password")
        self.assertEqual(rv.status_code, 200)
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="40"', rv.data)

        # user request
        rv = method("alice", "Alic3")
        self.assertEqual(rv.status_code, 200)
        self.assertIn('status="ok"', rv.data)

    def test_auth_basic(self):
        # No auth info
        rv = self.client.get("/rest/ping.view?c=tests")
        self.assertEqual(rv.status_code, 200)
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="10"', rv.data)

        self.__test_auth(self.__basic_auth_get)

        # Shouldn't accept 'enc:' passwords
        rv = self.__basic_auth_get("alice", "enc:" + hexlify("Alic3"))
        self.assertEqual(rv.status_code, 200)
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="40"', rv.data)

    def test_auth_query_params(self):
        self.__test_auth(self.__query_params_auth_get)
        self.__test_auth(self.__query_params_auth_enc_get)

    def test_auth_post(self):
        self.__test_auth(self.__form_auth_post)
        self.__test_auth(self.__form_auth_enc_post)

    def test_required_client(self):
        rv = self.client.get(
            "/rest/ping.view", query_string={"u": "alice", "p": "Alic3"}
        )
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="10"', rv.data)

        rv = self.client.get(
            "/rest/ping.view", query_string={"u": "alice", "p": "Alic3", "c": "tests"}
        )
        self.assertIn('status="ok"', rv.data)

    def test_format(self):
        args = {"u": "alice", "p": "Alic3", "c": "tests"}
        rv = self.client.get("/rest/getLicense.view", query_string=args)
        self.assertEqual(rv.status_code, 200)
        self.assertTrue(rv.mimetype.endswith("/xml"))  # application/xml or text/xml
        self.assertIn('status="ok"', rv.data)
        xml = ElementTree.fromstring(rv.data)
        self.assertIsNotNone(xml.find("./{http://subsonic.org/restapi}license"))

        args.update({"f": "json"})
        rv = self.client.get("/rest/getLicense.view", query_string=args)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, "application/json")
        json = flask.json.loads(rv.data)
        self.assertIn("subsonic-response", json)
        self.assertEqual(json["subsonic-response"]["status"], "ok")
        self.assertIn("license", json["subsonic-response"])

        args.update({"f": "jsonp"})
        rv = self.client.get("/rest/getLicense.view", query_string=args)
        self.assertEqual(rv.mimetype, "application/json")
        json = flask.json.loads(rv.data)
        self.assertIn("subsonic-response", json)
        self.assertEqual(json["subsonic-response"]["status"], "failed")
        self.assertEqual(json["subsonic-response"]["error"]["code"], 10)

        args.update({"callback": "dummy_cb"})
        rv = self.client.get("/rest/getLicense.view", query_string=args)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.mimetype, "application/javascript")
        self.assertTrue(rv.data.startswith("dummy_cb({"))
        self.assertTrue(rv.data.endswith("})"))
        json = flask.json.loads(rv.data[9:-1])
        self.assertIn("subsonic-response", json)
        self.assertEqual(json["subsonic-response"]["status"], "ok")
        self.assertIn("license", json["subsonic-response"])

    def test_not_implemented(self):
        # Access to not implemented/unknown endpoint
        rv = self.client.get(
            "/rest/unknown", query_string={"u": "alice", "p": "Alic3", "c": "tests"}
        )
        self.assertEqual(rv.status_code, 404)
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="0"', rv.data)

        rv = self.client.post(
            "/rest/unknown", data={"u": "alice", "p": "Alic3", "c": "tests"}
        )
        self.assertEqual(rv.status_code, 404)
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="0"', rv.data)

        rv = self.client.get(
            "/rest/getVideos.view",
            query_string={"u": "alice", "p": "Alic3", "c": "tests"},
        )
        self.assertEqual(rv.status_code, 200)
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="0"', rv.data)

        rv = self.client.post(
            "/rest/getVideos.view", data={"u": "alice", "p": "Alic3", "c": "tests"}
        )
        self.assertEqual(rv.status_code, 200)
        self.assertIn('status="failed"', rv.data)
        self.assertIn('code="0"', rv.data)


if __name__ == "__main__":
    unittest.main()

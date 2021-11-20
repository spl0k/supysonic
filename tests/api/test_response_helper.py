# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import flask.json

from xml.etree import ElementTree

from supysonic.api.formatters import JSONFormatter, JSONPFormatter, XMLFormatter

from ..testbase import TestBase


class UnwrapperMixin:
    def make_response(self, elem, data):
        with self.request_context():
            rv = super().make_response(elem, data)
            return rv.get_data(as_text=True)

    @staticmethod
    def create_from(cls):
        class Unwrapper(UnwrapperMixin, cls):
            pass

        return Unwrapper


class ResponseHelperJsonTestCase(TestBase, UnwrapperMixin.create_from(JSONFormatter)):
    def make_response(self, elem, data):
        rv = super().make_response(elem, data)
        return flask.json.loads(rv)

    def process_and_extract(self, d):
        return self.make_response("tag", d)["subsonic-response"]["tag"]

    def test_basic(self):
        empty = self.empty
        self.assertEqual(len(empty), 1)
        self.assertIn("subsonic-response", empty)
        self.assertIsInstance(empty["subsonic-response"], dict)

        resp = empty["subsonic-response"]
        self.assertEqual(len(resp), 2)
        self.assertIn("status", resp)
        self.assertIn("version", resp)
        self.assertEqual(resp["status"], "ok")

        resp = self.error(0, "message")["subsonic-response"]
        self.assertEqual(resp["status"], "failed")

        some_dict = {"intValue": 2, "someString": "Hello world!"}
        resp = self.process_and_extract(some_dict)
        self.assertIn("intValue", resp)
        self.assertIn("someString", resp)

    def test_lists(self):
        resp = self.process_and_extract({"someList": [2, 4, 8, 16], "emptyList": []})
        self.assertIn("someList", resp)
        self.assertNotIn("emptyList", resp)
        self.assertListEqual(resp["someList"], [2, 4, 8, 16])

    def test_dicts(self):
        resp = self.process_and_extract({"dict": {"s": "Blah", "i": 20}, "empty": {}})
        self.assertIn("dict", resp)
        self.assertIn("empty", resp)
        self.assertDictEqual(resp["dict"], {"s": "Blah", "i": 20})
        self.assertDictEqual(resp["empty"], {})

    def test_nesting(self):
        resp = self.process_and_extract(
            {
                "dict": {
                    "value": "hey look! a string",
                    "list": [1, 2, 3],
                    "emptyList": [],
                    "subdict": {"a": "A"},
                },
                "list": [{"b": "B"}, {"c": "C"}, [4, 5, 6], "final string"],
            }
        )

        self.assertEqual(len(resp), 2)
        self.assertIn("dict", resp)
        self.assertIn("list", resp)

        dct = resp["dict"]
        lst = resp["list"]

        self.assertIn("value", dct)
        self.assertIn("list", dct)
        self.assertNotIn("emptyList", dct)
        self.assertIn("subdict", dct)
        self.assertIsInstance(dct["value"], str)
        self.assertIsInstance(dct["list"], list)
        self.assertIsInstance(dct["subdict"], dict)

        self.assertEqual(lst, [{"b": "B"}, {"c": "C"}, [4, 5, 6], "final string"])


class ResponseHelperJsonpTestCase(TestBase, UnwrapperMixin.create_from(JSONPFormatter)):
    def test_basic(self):
        self._JSONPFormatter__callback = "callback"  # hacky
        result = self.empty
        self.assertTrue(result.startswith("callback({"))
        self.assertTrue(result.endswith("})"))

        json = flask.json.loads(result[9:-1])
        self.assertIn("subsonic-response", json)


class ResponseHelperXMLTestCase(TestBase, UnwrapperMixin.create_from(XMLFormatter)):
    def make_response(self, elem, data):
        xml = super().make_response(elem, data)
        xml = xml.replace('xmlns="http://subsonic.org/restapi"', "")
        root = ElementTree.fromstring(xml)
        return root

    def process_and_extract(self, d):
        rv = self.make_response("tag", d)
        return rv.find("tag")

    def assertAttributesMatchDict(self, elem, d):
        d = {k: str(v) for k, v in d.items()}
        self.assertDictEqual(elem.attrib, d)

    def test_root(self):
        xml = super().make_response("tag", {})
        self.assertIn("<subsonic-response ", xml)
        self.assertIn('xmlns="http://subsonic.org/restapi"', xml)
        self.assertTrue(xml.strip().endswith("</subsonic-response>"))

    def test_basic(self):
        empty = self.empty
        self.assertIsNotNone(empty.find(".[@version]"))
        self.assertIsNotNone(empty.find(".[@status='ok']"))

        resp = self.error(0, "message")
        self.assertIsNotNone(resp.find(".[@status='failed']"))

        some_dict = {"intValue": 2, "someString": "Hello world!"}
        resp = self.process_and_extract(some_dict)
        self.assertIsNotNone(resp.find(".[@intValue]"))
        self.assertIsNotNone(resp.find(".[@someString]"))

    def test_lists(self):
        resp = self.process_and_extract({"someList": [2, 4, 8, 16], "emptyList": []})

        elems = resp.findall("./someList")
        self.assertEqual(len(elems), 4)
        self.assertIsNone(resp.find("./emptyList"))

        for e, i in zip(elems, [2, 4, 8, 16]):
            self.assertEqual(int(e.text), i)

    def test_dicts(self):
        resp = self.process_and_extract({"dict": {"s": "Blah", "i": 20}, "empty": {}})

        d = resp.find("./dict")
        self.assertIsNotNone(d)
        self.assertIsNotNone(resp.find("./empty"))
        self.assertAttributesMatchDict(d, {"s": "Blah", "i": 20})

    def test_nesting(self):
        resp = self.process_and_extract(
            {
                "dict": {
                    "somevalue": "hey look! a string",
                    "list": [1, 2, 3],
                    "emptyList": [],
                    "subdict": {"a": "A"},
                },
                "list": [{"b": "B"}, {"c": "C"}, "final string"],
            }
        )

        self.assertEqual(len(resp), 4)  # 'dict' and 3 'list's

        d = resp.find("./dict")
        lists = resp.findall("./list")

        self.assertIsNotNone(d)
        self.assertAttributesMatchDict(d, {"somevalue": "hey look! a string"})
        self.assertEqual(len(d.findall("./list")), 3)
        self.assertEqual(len(d.findall("./emptyList")), 0)
        self.assertIsNotNone(d.find("./subdict"))

        self.assertEqual(len(lists), 3)
        self.assertAttributesMatchDict(lists[0], {"b": "B"})
        self.assertAttributesMatchDict(lists[1], {"c": "C"})
        self.assertEqual(lists[2].text, "final string")


if __name__ == "__main__":
    unittest.main()

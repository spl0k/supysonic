#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest, sys
from flask import Flask

import simplejson
from xml.etree import ElementTree

class AppMock(object):
    app = Flask(__name__)
    store = None

class ResponseHelperBaseCase(unittest.TestCase):
    def setUp(self):
        sys.modules[u'supysonic.web'] = AppMock()
        from supysonic.api import ResponseHelper
        self.helper = ResponseHelper

class ResponseHelperJsonTestCase(ResponseHelperBaseCase):
    def serialize_and_deserialize(self, d, error = False):
        if not isinstance(d, dict):
            raise TypeError(u'Invalid tested value, expecting a dict')

        json = self.helper.responsize_json(d, error)
        return simplejson.loads(json)

    def process_and_extract(self, d, error = False):
        # Basically returns d with additional version and status
        return self.serialize_and_deserialize(d, error)[u'subsonic-response']

    def test_basic(self):
        empty = self.serialize_and_deserialize({})
        self.assertEqual(len(empty), 1)
        self.assertIn(u'subsonic-response', empty)
        self.assertIsInstance(empty[u'subsonic-response'], dict)

        resp = empty[u'subsonic-response']
        self.assertEqual(len(resp), 2)
        self.assertIn(u'status', resp)
        self.assertIn(u'version', resp)
        self.assertEqual(resp[u'status'], u'ok')

        resp = self.process_and_extract({}, True)
        self.assertEqual(resp[u'status'], u'failed')

        some_dict = {
            u'intValue': 2,
            u'someString': u'Hello world!'
        }
        resp = self.process_and_extract(some_dict)
        self.assertIn(u'intValue', resp)
        self.assertIn(u'someString', resp)

    def test_lists(self):
        resp = self.process_and_extract({
            u'someList': [ 2, 4, 8, 16 ],
            u'emptyList': []
        })
        self.assertIn(u'someList', resp)
        self.assertNotIn(u'emptyList', resp)
        self.assertListEqual(resp[u'someList'], [ 2, 4, 8, 16 ])

    def test_dicts(self):
        resp = self.process_and_extract({
            u'dict': { u's': u'Blah', u'i': 20 },
            u'empty': {}
        })
        self.assertIn(u'dict', resp)
        self.assertIn(u'empty', resp)
        self.assertDictEqual(resp[u'dict'], { u's': u'Blah', u'i': 20 })
        self.assertDictEqual(resp[u'empty'], {})

    def test_nesting(self):
        resp = self.process_and_extract({
            u'dict': {
                u'value': u'hey look! a string',
                u'list': [ 1, 2, 3 ],
                u'emptyList': [],
                u'subdict': { u'a': u'A' }
            },
            u'list': [
                { u'b': u'B' },
                { u'c': u'C' },
                [ 4, 5, 6 ],
                u'final string'
            ]
        })

        self.assertEqual(len(resp), 4) # dict, list, status and version
        self.assertIn(u'dict', resp)
        self.assertIn(u'list', resp)

        d = resp[u'dict']
        l = resp[u'list']

        self.assertIn(u'value', d)
        self.assertIn(u'list', d)
        self.assertNotIn('emptyList', d)
        self.assertIn(u'subdict', d)
        self.assertIsInstance(d[u'value'], basestring)
        self.assertIsInstance(d[u'list'], list)
        self.assertIsInstance(d[u'subdict'], dict)

        self.assertEqual(l, [
            { u'b': u'B' },
            { u'c': u'C' },
            [ 4, 5, 6 ],
            u'final string'
        ])

class ResponseHelperJsonpTestCase(ResponseHelperBaseCase):
    def test_basic(self):
        result = self.helper.responsize_jsonp({}, u'callback')
        self.assertTrue(result.startswith(u'callback({'))
        self.assertTrue(result.endswith(u'})'))

        json = simplejson.loads(result[9:-1])
        self.assertIn(u'subsonic-response', json)

class ResponseHelperXMLTestCase(ResponseHelperBaseCase):
    def serialize_and_deserialize(self, d, error = False):
        xml = self.helper.responsize_xml(d, error)
        xml = xml.replace(u'xmlns="http://subsonic.org/restapi"', u'')
        root = ElementTree.fromstring(xml)
        return root

    def assertAttributesMatchDict(self, elem, d):
        d = { k: str(v) for k, v in d.iteritems() }
        self.assertDictEqual(elem.attrib, d)

    def test_root(self):
        xml = self.helper.responsize_xml({ 'tag': {}})
        self.assertIn(u'<subsonic-response ', xml)
        self.assertIn(u'xmlns="http://subsonic.org/restapi"', xml)
        self.assertTrue(xml.strip().endswith(u'</subsonic-response>'))

    def test_basic(self):
        empty = self.serialize_and_deserialize({})
        self.assertIsNotNone(empty.find(u'.[@version]'))
        self.assertIsNotNone(empty.find(u".[@status='ok']"))

        resp = self.serialize_and_deserialize({}, True)
        self.assertIsNotNone(resp.find(u".[@status='failed']"))

        some_dict = {
            u'intValue': 2,
            u'someString': u'Hello world!'
        }
        resp = self.serialize_and_deserialize(some_dict)
        self.assertIsNotNone(resp.find(u'.[@intValue]'))
        self.assertIsNotNone(resp.find(u'.[@someString]'))

    def test_lists(self):
        resp = self.serialize_and_deserialize({
            u'someList': [ 2, 4, 8, 16 ],
            u'emptyList': []
        })

        elems = resp.findall(u'./someList')
        self.assertEqual(len(elems), 4)
        self.assertIsNone(resp.find(u'./emptyList'))

        for e, i in zip(elems, [ 2, 4, 8, 16 ]):
            self.assertEqual(int(e.text), i)

    def test_dicts(self):
        resp = self.serialize_and_deserialize({
            u'dict': { u's': u'Blah', u'i': 20 },
            u'empty': {}
        })

        d = resp.find(u'./dict')
        self.assertIsNotNone(d)
        self.assertIsNotNone(resp.find(u'./empty'))
        self.assertAttributesMatchDict(d, { u's': u'Blah', u'i': 20 })

    def test_nesting(self):
        resp = self.serialize_and_deserialize({
            u'dict': {
                u'value': u'hey look! a string',
                u'list': [ 1, 2, 3 ],
                u'emptyList': [],
                u'subdict': { u'a': u'A' }
            },
            u'list': [
                { u'b': u'B' },
                { u'c': u'C' },
                u'final string'
            ]
        })

        self.assertEqual(len(resp), 4) # 'dict' and 3 'list's

        d = resp.find(u'./dict')
        lists = resp.findall(u'./list')

        self.assertIsNotNone(d)
        self.assertAttributesMatchDict(d, { u'value': u'hey look! a string' })
        self.assertEqual(len(d.findall(u'./list')), 3)
        self.assertEqual(len(d.findall(u'./emptyList')), 0)
        self.assertIsNotNone(d.find(u'./subdict'))

        self.assertEqual(len(lists), 3)
        self.assertAttributesMatchDict(lists[0], { u'b': u'B' })
        self.assertAttributesMatchDict(lists[1], { u'c': u'C' })
        self.assertEqual(lists[2].text, u'final string')

def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(ResponseHelperJsonTestCase))
    suite.addTest(unittest.makeSuite(ResponseHelperJsonpTestCase))
    suite.addTest(unittest.makeSuite(ResponseHelperXMLTestCase))

    return suite

if __name__ == '__main__':
    unittest.main()


#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import unittest
import flask.json

from xml.etree import ElementTree

from supysonic.py23 import strtype

from ..testbase import TestBase

class ResponseHelperBaseCase(TestBase):
    def setUp(self):
        super(ResponseHelperBaseCase, self).setUp()

        from supysonic.api.formatters import make_json_response, make_jsonp_response, make_xml_response
        self.json = self.__response_unwrapper(make_json_response)
        self.jsonp = self.__response_unwrapper(make_jsonp_response)
        self.xml = self.__response_unwrapper(make_xml_response)

    def __response_unwrapper(self, func):
        def execute(*args, **kwargs):
            with self.request_context():
                rv = func(*args, **kwargs)
                return rv.get_data(as_text = True)
        return execute

class ResponseHelperJsonTestCase(ResponseHelperBaseCase):
    def serialize_and_deserialize(self, d, error = False):
        if not isinstance(d, dict):
            raise TypeError('Invalid tested value, expecting a dict')

        json = self.json(d, error)
        return flask.json.loads(json)

    def process_and_extract(self, d, error = False):
        # Basically returns d with additional version and status
        return self.serialize_and_deserialize(d, error)['subsonic-response']

    def test_basic(self):
        empty = self.serialize_and_deserialize({})
        self.assertEqual(len(empty), 1)
        self.assertIn('subsonic-response', empty)
        self.assertIsInstance(empty['subsonic-response'], dict)

        resp = empty['subsonic-response']
        self.assertEqual(len(resp), 2)
        self.assertIn('status', resp)
        self.assertIn('version', resp)
        self.assertEqual(resp['status'], 'ok')

        resp = self.process_and_extract({}, True)
        self.assertEqual(resp['status'], 'failed')

        some_dict = {
            'intValue': 2,
            'someString': 'Hello world!'
        }
        resp = self.process_and_extract(some_dict)
        self.assertIn('intValue', resp)
        self.assertIn('someString', resp)

    def test_lists(self):
        resp = self.process_and_extract({
            'someList': [ 2, 4, 8, 16 ],
            'emptyList': []
        })
        self.assertIn('someList', resp)
        self.assertNotIn('emptyList', resp)
        self.assertListEqual(resp['someList'], [ 2, 4, 8, 16 ])

    def test_dicts(self):
        resp = self.process_and_extract({
            'dict': { 's': 'Blah', 'i': 20 },
            'empty': {}
        })
        self.assertIn('dict', resp)
        self.assertIn('empty', resp)
        self.assertDictEqual(resp['dict'], { 's': 'Blah', 'i': 20 })
        self.assertDictEqual(resp['empty'], {})

    def test_nesting(self):
        resp = self.process_and_extract({
            'dict': {
                'value': 'hey look! a string',
                'list': [ 1, 2, 3 ],
                'emptyList': [],
                'subdict': { 'a': 'A' }
            },
            'list': [
                { 'b': 'B' },
                { 'c': 'C' },
                [ 4, 5, 6 ],
                'final string'
            ]
        })

        self.assertEqual(len(resp), 4) # dict, list, status and version
        self.assertIn('dict', resp)
        self.assertIn('list', resp)

        d = resp['dict']
        l = resp['list']

        self.assertIn('value', d)
        self.assertIn('list', d)
        self.assertNotIn('emptyList', d)
        self.assertIn('subdict', d)
        self.assertIsInstance(d['value'], strtype)
        self.assertIsInstance(d['list'], list)
        self.assertIsInstance(d['subdict'], dict)

        self.assertEqual(l, [
            { 'b': 'B' },
            { 'c': 'C' },
            [ 4, 5, 6 ],
            'final string'
        ])

class ResponseHelperJsonpTestCase(ResponseHelperBaseCase):
    def test_basic(self):
        result = self.jsonp({}, 'callback')
        self.assertTrue(result.startswith('callback({'))
        self.assertTrue(result.endswith('})'))

        json = flask.json.loads(result[9:-1])
        self.assertIn('subsonic-response', json)

class ResponseHelperXMLTestCase(ResponseHelperBaseCase):
    def serialize_and_deserialize(self, d, error = False):
        xml = self.xml(d, error)
        xml = xml.replace('xmlns="http://subsonic.org/restapi"', '')
        root = ElementTree.fromstring(xml)
        return root

    def assertAttributesMatchDict(self, elem, d):
        d = { k: str(v) for k, v in d.items() }
        self.assertDictEqual(elem.attrib, d)

    def test_root(self):
        xml = self.xml({ 'tag': {}})
        self.assertIn('<subsonic-response ', xml)
        self.assertIn('xmlns="http://subsonic.org/restapi"', xml)
        self.assertTrue(xml.strip().endswith('</subsonic-response>'))

    def test_basic(self):
        empty = self.serialize_and_deserialize({})
        self.assertIsNotNone(empty.find('.[@version]'))
        self.assertIsNotNone(empty.find(".[@status='ok']"))

        resp = self.serialize_and_deserialize({}, True)
        self.assertIsNotNone(resp.find(".[@status='failed']"))

        some_dict = {
            'intValue': 2,
            'someString': 'Hello world!'
        }
        resp = self.serialize_and_deserialize(some_dict)
        self.assertIsNotNone(resp.find('.[@intValue]'))
        self.assertIsNotNone(resp.find('.[@someString]'))

    def test_lists(self):
        resp = self.serialize_and_deserialize({
            'someList': [ 2, 4, 8, 16 ],
            'emptyList': []
        })

        elems = resp.findall('./someList')
        self.assertEqual(len(elems), 4)
        self.assertIsNone(resp.find('./emptyList'))

        for e, i in zip(elems, [ 2, 4, 8, 16 ]):
            self.assertEqual(int(e.text), i)

    def test_dicts(self):
        resp = self.serialize_and_deserialize({
            'dict': { 's': 'Blah', 'i': 20 },
            'empty': {}
        })

        d = resp.find('./dict')
        self.assertIsNotNone(d)
        self.assertIsNotNone(resp.find('./empty'))
        self.assertAttributesMatchDict(d, { 's': 'Blah', 'i': 20 })

    def test_nesting(self):
        resp = self.serialize_and_deserialize({
            'dict': {
                'value': 'hey look! a string',
                'list': [ 1, 2, 3 ],
                'emptyList': [],
                'subdict': { 'a': 'A' }
            },
            'list': [
                { 'b': 'B' },
                { 'c': 'C' },
                'final string'
            ]
        })

        self.assertEqual(len(resp), 4) # 'dict' and 3 'list's

        d = resp.find('./dict')
        lists = resp.findall('./list')

        self.assertIsNotNone(d)
        self.assertAttributesMatchDict(d, { 'value': 'hey look! a string' })
        self.assertEqual(len(d.findall('./list')), 3)
        self.assertEqual(len(d.findall('./emptyList')), 0)
        self.assertIsNotNone(d.find('./subdict'))

        self.assertEqual(len(lists), 3)
        self.assertAttributesMatchDict(lists[0], { 'b': 'B' })
        self.assertAttributesMatchDict(lists[1], { 'c': 'C' })
        self.assertEqual(lists[2].text, 'final string')

def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(ResponseHelperJsonTestCase))
    suite.addTest(unittest.makeSuite(ResponseHelperJsonpTestCase))
    suite.addTest(unittest.makeSuite(ResponseHelperXMLTestCase))

    return suite

if __name__ == '__main__':
    unittest.main()


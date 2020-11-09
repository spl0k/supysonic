# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2017-2020 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import re

from lxml import etree
from supysonic.managers.user import UserManager

from ..testbase import TestBase

path_replace_regexp = re.compile(r"/(\w+)")

NS = "http://subsonic.org/restapi"
NSMAP = {"sub": NS}


class ApiTestBase(TestBase):
    __with_api__ = True

    def setUp(self):
        super(ApiTestBase, self).setUp()

        xsd = etree.parse("tests/assets/subsonic-rest-api-1.10.2.xsd")
        self.schema = etree.XMLSchema(xsd)

    def _find(self, xml, path):
        """
        Helper method that insert the namespace in ElementPath 'path'
        """

        path = path_replace_regexp.sub(r"/{{{}}}\1".format(NS), path)
        return xml.find(path)

    def _xpath(self, elem, path):
        """
        Helper method that insert a prefix and map the namespace in XPath 'path'
        """

        path = path_replace_regexp.sub(r"/sub:\1", path)
        return elem.xpath(path, namespaces=NSMAP)

    def _make_request(self, endpoint, args={}, tag=None, error=None, skip_post=False):
        """
        Makes both a GET and POST requests against the API, assert both get the same response.
        If the user isn't provided with the 'u' and 'p' in 'args', the default 'alice' is used.
        Validate the response against the Subsonic API XSD and assert it matches the expected tag or error.

        :param endpoint: request endpoint, with the '/rest/'prefix nor the '.view' suffix
        :param args: dict of parameters. 'u', 'p', 'c' and 'v' are automatically added
        :param tag: topmost expected element, right beneath 'subsonic-response'
        :param error: if the given 'args' should produce an error at 'endpoint', this is the expected error code
        :param skip_post: don't do the POST request

        :return: a 2-tuple (resp, child) if no error, where 'resp' is the full response object, 'child' a
            'lxml.etree.Element' mathching 'tag' (if any). If there's an error (when expected), only returns
            the response object
        """

        if not isinstance(args, dict):
            raise TypeError("'args', expecting a dict, got " + type(args).__name__)
        if tag and not isinstance(tag, str):
            raise TypeError("'tag', expecting a str, got " + type(tag).__name__)

        args.update({"c": "tests", "v": "1.9.0"})
        if "u" not in args:
            args.update({"u": "alice", "p": "Alic3"})

        uri = "/rest/{}.view".format(endpoint)
        rg = self.client.get(uri, query_string=args)
        if not skip_post:
            rp = self.client.post(uri, data=args)
            self.assertEqual(rg.data, rp.data)

        xml = etree.fromstring(rg.data)
        self.schema.assert_(xml)

        if xml.get("status") == "ok":
            self.assertIsNone(error)
            if tag:
                self.assertEqual(xml[0].tag, "{{{}}}{}".format(NS, tag))
                return rg, xml[0]
            else:
                self.assertEqual(len(xml), 0)
                return rg, None
        else:
            self.assertIsNone(tag)
            self.assertEqual(xml[0].tag, "{{{}}}error".format(NS))
            self.assertEqual(xml[0].get("code"), str(error))
            return rg

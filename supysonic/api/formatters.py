# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import json, jsonify, make_response
from xml.etree import ElementTree

from . import API_VERSION


class BaseFormatter:
    def make_response(self, elem, data):
        raise NotImplementedError()

    def make_error(self, code, message):
        return self.make_response("error", {"code": code, "message": message})

    def make_empty(self):
        return self.make_response(None, None)

    def __call__(self, *args, **kwargs):
        return self.make_response(*args, **kwargs)

    error = make_error
    empty = property(make_empty)


class JSONBaseFormatter(BaseFormatter):
    def __remove_empty_lists(self, d):
        if not isinstance(d, dict):
            raise TypeError("Expecting a dict got " + type(d).__name__)

        keys_to_remove = []
        for key, value in d.items():
            if isinstance(value, dict):
                d[key] = self.__remove_empty_lists(value)
            elif isinstance(value, list):
                if len(value) == 0:
                    keys_to_remove.append(key)
                else:
                    d[key] = [
                        (
                            self.__remove_empty_lists(item)
                            if isinstance(item, dict)
                            else item
                        )
                        for item in value
                    ]

        for key in keys_to_remove:
            del d[key]

        return d

    def _subsonicify(self, elem, data):
        if (elem is None) != (data is None):
            raise ValueError("Expecting both elem and data or neither of them")

        rv = {"status": "failed" if elem == "error" else "ok", "version": API_VERSION}
        if data:
            rv[elem] = self.__remove_empty_lists(data)

        return {"subsonic-response": rv}


class JSONFormatter(JSONBaseFormatter):
    def make_response(self, elem, data):
        rv = jsonify(self._subsonicify(elem, data))
        rv.headers.add("Access-Control-Allow-Origin", "*")
        return rv


class JSONPFormatter(JSONBaseFormatter):
    def __init__(self, callback):
        self.__callback = callback

    def make_response(self, elem, data):
        if not self.__callback:
            return jsonify(
                self._subsonicify("error", {"code": 10, "message": "Missing callback"})
            )

        rv = self._subsonicify(elem, data)
        rv = f"{self.__callback}({json.dumps(rv)})"
        rv = make_response(rv)
        rv.mimetype = "application/javascript"
        return rv


class XMLFormatter(BaseFormatter):
    def __dict2xml(self, elem, dictionary):
        """Convert a dict structure to xml. The game is trivial. Nesting uses the [] parenthesis.
        ex.  { 'musicFolder': {'id': 1234, 'name': "sss" } }
          ex. { 'musicFolder': [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }]}
          ex. { 'musicFolders': {'musicFolder' : [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }] } }
          ex. { 'index': [{'name': 'A',  'artist': [{'id': '517674445', 'name': 'Antonello Venditti'}] }] }
          ex. {"subsonic-response": { "musicFolders": {"musicFolder": [{ "id": 0,"name": "Music"}]},
          "status": "ok","version": "1.7.0","xmlns": "http://subsonic.org/restapi"}}
        """
        if not isinstance(dictionary, dict):
            raise TypeError("Expecting a dict")
        if not all(isinstance(x, str) for x in dictionary):
            raise TypeError("Dictionary keys must be strings")

        for name, value in dictionary.items():
            if name == "value":
                elem.text = self.__value_tostring(value)
            elif isinstance(value, dict):
                subelem = ElementTree.SubElement(elem, name)
                self.__dict2xml(subelem, value)
            elif isinstance(value, list):
                for v in value:
                    subelem = ElementTree.SubElement(elem, name)
                    if isinstance(v, dict):
                        self.__dict2xml(subelem, v)
                    else:
                        subelem.text = self.__value_tostring(v)
            else:
                elem.set(name, self.__value_tostring(value))

    def __value_tostring(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    def make_response(self, elem, data):
        if (elem is None) != (data is None):
            raise ValueError("Expecting both elem and data or neither of them")

        response = {
            "status": "failed" if elem == "error" else "ok",
            "version": API_VERSION,
            "xmlns": "http://subsonic.org/restapi",
        }
        if elem:
            response[elem] = data

        root = ElementTree.Element("subsonic-response")
        self.__dict2xml(root, response)

        rv = make_response(ElementTree.tostring(root))
        rv.mimetype = "text/xml"
        return rv

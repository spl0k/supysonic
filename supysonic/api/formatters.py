# coding: utf-8
#
# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

from flask import json, jsonify, make_response
from xml.dom import minidom
from xml.etree import ElementTree

from ..py23 import dict, strtype
from . import API_VERSION

def remove_empty_lists(d):
    if not isinstance(d, dict):
        raise TypeError('Expecting a dict got ' + type(d).__name__)

    keys_to_remove = []
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = remove_empty_lists(value)
        elif isinstance(value, list):
            if len(value) == 0:
                keys_to_remove.append(key)
            else:
                d[key] = [ remove_empty_lists(item) if isinstance(item, dict) else item for item in value ]

    for key in keys_to_remove:
        del d[key]

    return d

def subsonicify(response, error):
    rv = remove_empty_lists(response)

    # add headers to response
    rv.update(
        status = 'failed' if error else 'ok',
        version = API_VERSION
    )
    return { 'subsonic-response': rv }

def dict2xml(elem, dictionary):
    """Convert a json structure to xml. The game is trivial. Nesting uses the [] parenthesis.
      ex.  { 'musicFolder': {'id': 1234, 'name': "sss" } }
        ex. { 'musicFolder': [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }]}
        ex. { 'musicFolders': {'musicFolder' : [{'id': 1234, 'name': "sss" }, {'id': 456, 'name': "aaa" }] } }
        ex. { 'index': [{'name': 'A',  'artist': [{'id': '517674445', 'name': 'Antonello Venditti'}] }] }
        ex. {"subsonic-response": { "musicFolders": {"musicFolder": [{ "id": 0,"name": "Music"}]},
        "status": "ok","version": "1.7.0","xmlns": "http://subsonic.org/restapi"}}
    """
    if not isinstance(dictionary, dict):
        raise TypeError('Expecting a dict')
    if not all(map(lambda x: isinstance(x, strtype), dictionary)):
        raise TypeError('Dictionary keys must be strings')

    for name, value in dictionary.items():
        if name == '_value_':
            elem.text = value_tostring(value)
        elif isinstance(value, dict):
            subelem = ElementTree.SubElement(elem, name)
            dict2xml(subelem, value)
        elif isinstance(value, list):
            for v in value:
                subelem = ElementTree.SubElement(elem, name)
                if isinstance(v, dict):
                    dict2xml(subelem, v)
                else:
                    subelem.text = value_tostring(v)
        else:
            elem.set(name, value_tostring(value))

def value_tostring(value):
    if value is None:
        return None
    if isinstance(value, strtype):
        return value
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)

def make_json_response(response, error = False):
    rv = jsonify(subsonicify(response, error))
    rv.headers.add('Access-Control-Allow-Origin', '*')
    return rv

def make_jsonp_response(response, callback, error = False):
    if not callback:
        return make_json_response(dict(error = dict(code = 10, message = 'Missing callback')), error = True)

    rv = subsonicify(response, error)
    rv = '{}({})'.format(callback, json.dumps(rv))
    rv = make_response(rv)
    rv.mimetype = 'application/javascript'
    return rv

def make_xml_response(response, error = False):
    response.update(
        status = 'failed' if error else 'ok',
        version = API_VERSION,
        xmlns = "http://subsonic.org/restapi"
    )

    elem = ElementTree.Element('subsonic-response')
    dict2xml(elem, response)

    rv = minidom.parseString(ElementTree.tostring(elem)).toprettyxml(indent = '  ')
    rv = make_response(rv)
    rv.mimetype = 'text/xml'
    return rv

def make_error_response_func(f):
    def make_error_response(code, message):
        return f(dict(error = dict(code = code, message = message)), error = True)
    return make_error_response


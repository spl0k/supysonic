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

import unittest
import io, re
from collections import namedtuple
import uuid

from supysonic import db

date_regex = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')

class DbTestCase(unittest.TestCase):
    def setUp(self):
        self.store = db.get_store(u'sqlite:')
        with io.open(u'schema/sqlite.sql', u'r') as f:
            for statement in f.read().split(u';'):
                    self.store.execute(statement)

    def tearDown(self):
        self.store.close()

    def create_some_folders(self):
        root_folder = db.Folder()
        root_folder.root = True
        root_folder.name = u'Root folder'
        root_folder.path = u'/'

        child_folder = db.Folder()
        child_folder.root = False
        child_folder.name = u'Child folder'
        child_folder.path = u'/child'
        child_folder.has_cover_art = True
        child_folder.parent = root_folder

        self.store.add(root_folder)
        self.store.add(child_folder)
        self.store.commit()

        return root_folder, child_folder

    def test_folder_base(self):
        root_folder, child_folder = self.create_some_folders()

        MockUser = namedtuple(u'User', [ u'id' ])
        user = MockUser(uuid.uuid4())

        root = root_folder.as_subsonic_child(user)
        self.assertIsInstance(root, dict)
        self.assertIn(u'id', root)
        self.assertIn(u'isDir', root)
        self.assertIn(u'title', root)
        self.assertIn(u'album', root)
        self.assertIn(u'created', root)
        self.assertTrue(root[u'isDir'])
        self.assertEqual(root[u'title'], u'Root folder')
        self.assertEqual(root[u'album'], u'Root folder')
        self.assertTrue(date_regex.match(root['created']))

        child = child_folder.as_subsonic_child(user)
        self.assertIn(u'parent', child)
        self.assertIn(u'artist', child)
        self.assertIn(u'coverArt', child)
        self.assertEqual(child[u'parent'], str(root_folder.id))
        self.assertEqual(child[u'artist'], root_folder.name)
        self.assertEqual(child[u'coverArt'], child[u'id'])

    def test_folder_annotation(self):
        root_folder, child_folder = self.create_some_folders()

        # Assuming SQLite doesn't enforce foreign key constraints
        MockUser = namedtuple(u'User', [ u'id' ])
        user = MockUser(uuid.uuid4())

        star = db.StarredFolder()
        star.user_id = user.id
        star.starred_id = root_folder.id

        rating_user = db.RatingFolder()
        rating_user.user_id = user.id
        rating_user.rated_id = root_folder.id
        rating_user.rating = 2

        rating_other = db.RatingFolder()
        rating_other.user_id = uuid.uuid4()
        rating_other.rated_id = root_folder.id
        rating_other.rating = 5

        self.store.add(star)
        self.store.add(rating_user)
        self.store.add(rating_other)

        root = root_folder.as_subsonic_child(user)
        self.assertIn(u'starred', root)
        self.assertIn(u'userRating', root)
        self.assertIn(u'averageRating', root)
        self.assertTrue(date_regex.match(root[u'starred']))
        self.assertEqual(root[u'userRating'], 2)
        self.assertEqual(root[u'averageRating'], 3.5)

        child = child_folder.as_subsonic_child(user)
        self.assertNotIn(u'starred', child)
        self.assertNotIn(u'userRating', child)


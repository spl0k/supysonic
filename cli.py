#!/usr/bin/python
# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013, 2014  Alban 'spl0k' Féron
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import config
config.check()

from web import app
from flask.ext.script import Manager, Command, Option, prompt_pass
import os.path
from managers.folder import FolderManager
from managers.user import UserManager
from scanner import Scanner

from db import User, Folder, session, metadata

manager = Manager(app)

@manager.command
def folder_list():
    "Lists all Folders to Scan"
    print 'Name\t\tPath\n----\t\t----'
    print '\n'.join('{0: <16}{1}'.format(f.name, f.path) for f in session.query(Folder).filter(Folder.root == True))


@manager.command
def folder_add(path):
    "Add a folder to the Library"
    ret = FolderManager.add(path)
    if ret != FolderManager.SUCCESS:
        print FolderManager.error_str(ret)
    else:
        print "Folder '{}' added".format(path)

@manager.command
def folder_delete(path):
    "Delete folder from Library"

    s = Scanner(session)

    ret = FolderManager.delete_by_name(path, s)
    if ret != FolderManager.SUCCESS:
        print FolderManager.error_str(ret)
    else:
        print "Deleted folder" + path

@manager.command
def folder_scan():
    s = Scanner(session)

    folders = session.query(Folder).filter(Folder.root == True)

    if folders:
        for folder in folders:
            print "Scanning: " + folder.path
            FolderManager.scan(folder.id, s)

        added, deleted = s.stats()

        print "\a"
        print "Scanning done"
        print 'Added: %i artists, %i albums, %i tracks' % (added[0], added[1], added[2])
        print 'Deleted: %i artists, %i albums, %i tracks' % (deleted[0], deleted[1], deleted[2])

@manager.command
def folder_prune():
    s = Scanner(session)

    folders = session.query(Folder).filter(Folder.root == True)

    if folders:
        for folder in folders:
            print "Pruning: " + folder.path
            FolderManager.prune(folder.id, s)

        added, deleted = s.stats()

        print "\a"
        print "Pruning done"
        print 'Added: %i artists, %i albums, %i tracks' % (added[0], added[1], added[2])
        print 'Deleted: %i artists, %i albums, %i tracks' % (deleted[0], deleted[1], deleted[2])

@manager.command
def user_list():
    print 'Name\t\tAdmin\tEmail\n----\t\t-----\t-----'
    print '\n'.join('{0: <16}{1}\t{2}'.format(u.name, '*' if u.admin else '', u.mail) for u in session.query(User).all())

@manager.command
def user_add(name, admin=False, email=None):
    password = prompt_pass("Please enter a password")
    if password:
        status = UserManager.add(name, password, email, admin)
        if status != UserManager.SUCCESS:
            print >>sys.stderr, UserManager.error_str(status)

@manager.command
def user_delete(name):
    user = session.query(User).filter(User.name == name).first()
    if not user:
        print >>sys.stderr, 'No such user'
    else:
        session.delete(user)
        session.commit()
        print "User '{}' deleted".format(name)

@manager.command
def user_setadmin(name, off):
    user = session.query(User).filter(User.name == name).first()
    if not user:
        print >>sys.stderr, 'No such user'
    else:
        user.admin = not off
        session.commit()
        print "{0} '{1}' admin rights".format('Revoked' if off else 'Granted', name)

@manager.command
def user_changepass(name, password):
    if not password:
        password = getpass.getpass()
        confirm  = getpass.getpass('Confirm password: ')
        if password != confirm:
            print >>sys.stderr, "Passwords don't match"
            return
        status = UserManager.change_password2(name, password)
        if status != UserManager.SUCCESS:
            print >>sys.stderr, UserManager.error_str(status)
        else:
            print "Successfully changed '{}' password".format(name)

@manager.command
def recreate_db():
    with app.app_context():
        metadata.drop_all()
        metadata.create_all()

if __name__ == "__main__":
    import config

    if not config.check():
        sys.exit(1)

    if not os.path.exists(config.get('base', 'cache_dir')):
        os.makedirs(config.get('base', 'cache_dir'))

    manager.run()

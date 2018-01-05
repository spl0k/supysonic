#!/usr/bin/env python
# coding: utf-8

# This file is part of Supysonic.
#
# Supysonic is a Python implementation of the Subsonic server API.
# Copyright (C) 2013-2018  Alban 'spl0k' Féron
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

import argparse
import cmd
import getpass
import sys
import time

from pony.orm import db_session

from .db import Folder, User
from .managers.folder import FolderManager
from .managers.user import UserManager
from .scanner import Scanner

class TimedProgressDisplay:
    def __init__(self, name, stdout, interval = 5):
        self.__name = name
        self.__stdout = stdout
        self.__interval = interval
        self.__last_display = 0
        self.__last_len = 0

    def __call__(self, scanned, total):
        if time.time() - self.__last_display > self.__interval or scanned == total:
            if not self.__last_len:
                self.__stdout.write("Scanning '{0}': ".format(self.__name))

            progress = "{0}% ({1}/{2})".format((scanned * 100) / total, scanned, total)
            self.__stdout.write('\b' * self.__last_len)
            self.__stdout.write(progress)
            self.__stdout.flush()

            self.__last_len = len(progress)
            self.__last_display = time.time()

class CLIParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        raise RuntimeError(message)

class SupysonicCLI(cmd.Cmd):
    prompt = "supysonic> "

    def _make_do(self, command):
        def method(obj, line):
            try:
                args = getattr(obj, command + '_parser').parse_args(line.split())
            except RuntimeError as e:
                self.write_error_line(str(e))
                return

            if hasattr(obj.__class__, command + '_subparsers'):
                try:
                    func = getattr(obj, '{}_{}'.format(command, args.action))
                except AttributeError:
                    return obj.default(line)
                return func(** { key: vars(args)[key] for key in vars(args) if key != 'action' })
            else:
                try:
                    func = getattr(obj, command)
                except AttributeError:
                    return obj.default(line)
                return func(**vars(args))

        return method

    def __init__(self, config, stderr=None, *args, **kwargs):
        cmd.Cmd.__init__(self, *args, **kwargs)

        if stderr is not None:
            self.stderr = stderr
        else:
            self.stderr = sys.stderr

        self.__config = config

        # Generate do_* and help_* methods
        for parser_name in filter(lambda attr: attr.endswith('_parser') and '_' not in attr[:-7], dir(self.__class__)):
            command = parser_name[:-7]

            if not hasattr(self.__class__, 'do_' + command):
                setattr(self.__class__, 'do_' + command, self._make_do(command))

            if hasattr(self.__class__, 'do_' + command) and not hasattr(self.__class__, 'help_' + command):
                setattr(self.__class__, 'help_' + command, getattr(self.__class__, parser_name).print_help)
            if hasattr(self.__class__, command + '_subparsers'):
                for action, subparser in getattr(self.__class__, command + '_subparsers').choices.items():
                    setattr(self, 'help_{} {}'.format(command, action), subparser.print_help)

    def write_line(self, line = ''):
        self.stdout.write(line + '\n')

    def write_error_line(self, line = ''):
        self.stderr.write(line + '\n')

    def do_EOF(self, line):
        return True

    do_exit = do_EOF

    def default(self, line):
        self.write_line('Unknown command %s' % line.split()[0])
        self.do_help(None)

    def postloop(self):
        self.write_line()

    def completedefault(self, text, line, begidx, endidx):
        command = line.split()[0]
        parsers = getattr(self.__class__, command + '_subparsers', None)
        if not parsers:
            return []

        num_words = len(line[len(command):begidx].split())
        if num_words == 0:
            return [ a for a in parsers.choices if a.startswith(text) ]
        return []

    folder_parser = CLIParser(prog = 'folder', add_help = False)
    folder_subparsers = folder_parser.add_subparsers(dest = 'action')
    folder_subparsers.add_parser('list', help = 'Lists folders', add_help = False)
    folder_add_parser = folder_subparsers.add_parser('add', help = 'Adds a folder', add_help = False)
    folder_add_parser.add_argument('name', help = 'Name of the folder to add')
    folder_add_parser.add_argument('path', help = 'Path to the directory pointed by the folder')
    folder_del_parser = folder_subparsers.add_parser('delete', help = 'Deletes a folder', add_help = False)
    folder_del_parser.add_argument('name', help = 'Name of the folder to delete')
    folder_scan_parser = folder_subparsers.add_parser('scan', help = 'Run a scan on specified folders', add_help = False)
    folder_scan_parser.add_argument('folders', metavar = 'folder', nargs = '*', help = 'Folder(s) to be scanned. If ommitted, all folders are scanned')
    folder_scan_parser.add_argument('-f', '--force', action = 'store_true', help = "Force scan of already know files even if they haven't changed")

    @db_session
    def folder_list(self):
        self.write_line('Name\t\tPath\n----\t\t----')
        self.write_line('\n'.join('{0: <16}{1}'.format(f.name, f.path) for f in Folder.select(lambda f: f.root)))

    def folder_add(self, name, path):
        ret = FolderManager.add(name, path)
        if ret != FolderManager.SUCCESS:
            self.write_error_line(FolderManager.error_str(ret))
        else:
            self.write_line("Folder '{}' added".format(name))

    def folder_delete(self, name):
        ret = FolderManager.delete_by_name(name)
        if ret != FolderManager.SUCCESS:
            self.write_error_line(FolderManager.error_str(ret))
        else:
            self.write_line("Deleted folder '{}'".format(name))

    @db_session
    def folder_scan(self, folders, force):
        extensions = self.__config.BASE['scanner_extensions']
        if extensions:
            extensions = extensions.split(' ')

        scanner = Scanner(force = force, extensions = extensions)

        if folders:
            fstrs = folders
            folders = Folder.select(lambda f: f.root and f.name in fstrs)[:]
            notfound = set(fstrs) - set(map(lambda f: f.name, folders))
            if notfound:
                self.write_line("No such folder(s): " + ' '.join(notfound))
            for folder in folders:
                scanner.scan(folder, TimedProgressDisplay(folder.name, self.stdout))
                self.write_line()
        else:
            for folder in Folder.select(lambda f: f.root):
                scanner.scan(folder, TimedProgressDisplay(folder.name, self.stdout))
                self.write_line()

        scanner.finish()
        added, deleted = scanner.stats()

        self.write_line("Scanning done")
        self.write_line('Added: %i artists, %i albums, %i tracks' % (added[0], added[1], added[2]))
        self.write_line('Deleted: %i artists, %i albums, %i tracks' % (deleted[0], deleted[1], deleted[2]))

    user_parser = CLIParser(prog = 'user', add_help = False)
    user_subparsers = user_parser.add_subparsers(dest = 'action')
    user_subparsers.add_parser('list', help = 'List users', add_help = False)
    user_add_parser = user_subparsers.add_parser('add', help = 'Adds a user', add_help = False)
    user_add_parser.add_argument('name', help = 'Name/login of the user to add')
    user_add_parser.add_argument('-a', '--admin', action = 'store_true', help = 'Give admin rights to the new user')
    user_add_parser.add_argument('-p', '--password', help = "Specifies the user's password")
    user_add_parser.add_argument('-e', '--email', default = '', help = "Sets the user's email address")
    user_del_parser = user_subparsers.add_parser('delete', help = 'Deletes a user', add_help = False)
    user_del_parser.add_argument('name', help = 'Name/login of the user to delete')
    user_admin_parser = user_subparsers.add_parser('setadmin', help = 'Enable/disable admin rights for a user', add_help = False)
    user_admin_parser.add_argument('name', help = 'Name/login of the user to grant/revoke admin rights')
    user_admin_parser.add_argument('--off', action = 'store_true', help = 'Revoke admin rights if present, grant them otherwise')
    user_pass_parser = user_subparsers.add_parser('changepass', help = "Changes a user's password", add_help = False)
    user_pass_parser.add_argument('name', help = 'Name/login of the user to which change the password')
    user_pass_parser.add_argument('password', nargs = '?', help = 'New password')

    @db_session
    def user_list(self):
        self.write_line('Name\t\tAdmin\tEmail\n----\t\t-----\t-----')
        self.write_line('\n'.join('{0: <16}{1}\t{2}'.format(u.name, '*' if u.admin else '', u.mail) for u in User.select()))

    def user_add(self, name, admin, password, email):
        if not password:
            password = getpass.getpass()
            confirm  = getpass.getpass('Confirm password: ')
            if password != confirm:
                self.write_error_line("Passwords don't match")
                return
        status = UserManager.add(name, password, email, admin)
        if status != UserManager.SUCCESS:
            self.write_error_line(UserManager.error_str(status))

    def user_delete(self, name):
        ret = UserManager.delete_by_name(name)
        if ret != UserManager.SUCCESS:
            self.write_error_line(UserManager.error_str(ret))
        else:
            self.write_line("Deleted user '{}'".format(name))

    @db_session
    def user_setadmin(self, name, off):
        user = User.get(name = name)
        if user is None:
            self.write_error_line('No such user')
        else:
            user.admin = not off
            self.write_line("{0} '{1}' admin rights".format('Revoked' if off else 'Granted', name))

    def user_changepass(self, name, password):
        if not password:
            password = getpass.getpass()
            confirm  = getpass.getpass('Confirm password: ')
            if password != confirm:
                self.write_error_line("Passwords don't match")
                return
        status = UserManager.change_password2(name, password)
        if status != UserManager.SUCCESS:
            self.write_error_line(UserManager.error_str(status))
        else:
            self.write_line("Successfully changed '{}' password".format(name))


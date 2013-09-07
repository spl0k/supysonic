# coding: utf-8

import sys, cmd, argparse, getpass
import config

class CLIParser(argparse.ArgumentParser):
	def error(self, message):
		self.print_usage(sys.stderr)
		raise RuntimeError(message)

class CLI(cmd.Cmd):
	prompt = "supysonic> "

	def do_EOF(self, line):
		return True

	def default(self, line):
		print 'Unknown command %s' % line.split()[0]
		self.do_help(None)

	def postloop(self):
		print

	def completedefault(self, text, line, begidx, endidx):
		command = line.split()[0]
		parsers = getattr(self, command + '_subparsers', None)
		if not parsers:
			return []

		num_words = len(line[len(command):begidx].split())
		if num_words == 0:
			return [ a for a in parsers.choices.keys() if a.startswith(text) ]
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

	def do_folder(self, line):
		try:
			args = self.folder_parser.parse_args(line.split())
		except RuntimeError, e:
			print >>sys.stderr, e
			return

		if args.action == 'list':
			print 'Name\t\tPath\n----\t\t----'
			print '\n'.join('{0: <16}{1}'.format(f.name, f.path) for f in db.Folder.query.filter(db.Folder.root == True))
		elif args.action == 'add':
			ret = FolderManager.add(args.name, args.path)
			if ret != FolderManager.SUCCESS:
				print FolderManager.error_str(ret)
			else:
				print "Folder '%s' added" % args.name
		elif args.action == 'delete':
			ret = FolderManager.delete_by_name(args.name)
			if ret != FolderManager.SUCCESS:
				print FolderManager.error_str(ret)
			else:
				print "Deleted folder '%s'" % args.name
		elif args.action == 'scan':
			s = Scanner(db.session)
			if args.folders:
				folders = map(lambda n: db.Folder.query.filter(db.Folder.name == n and db.Folder.root == True).first() or n, args.folders)
				if any(map(lambda f: isinstance(f, basestring), folders)):
					print "No such folder(s): " + ' '.join(f for f in folders if isinstance(f, basestring))
				for folder in filter(lambda f: isinstance(f, db.Folder), folders):
					FolderManager.scan(folder.id, s)
			else:
				for folder in db.Folder.query.filter(db.Folder.root == True):
					FolderManager.scan(folder.id, s)

			added, deleted = s.stats()
			db.session.commit()

			print "Scanning done"
			print 'Added: %i artists, %i albums, %i tracks' % (added[0], added[1], added[2])
			print 'Deleted: %i artists, %i albums, %i tracks' % (deleted[0], deleted[1], deleted[2])

	def help_folder(self):
		self.folder_parser.print_help()
		#for cmd, parser in self.folder_subparsers.choices.iteritems():
		#	parser.print_help()

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
	user_admin_parser = user_subparsers.add_parser('set-admin', help = 'Enable/disable admin rights for a user', add_help = False)
	user_admin_parser.add_argument('name', help = 'Name/login of the user to grant/revoke admin rights')
	user_admin_parser.add_argument('--off', action = 'store_true', help = 'Revoke admin rights if present, grant them otherwise')
	user_pass_parser = user_subparsers.add_parser('changepass', help = "Changes a user's password", add_help = False)
	user_pass_parser.add_argument('name', help = 'Name/login of the user to which change the password')
	user_pass_parser.add_argument('password', nargs = '?', help = 'New password')

	def do_user(self, line):
		try:
			args = self.user_parser.parse_args(line.split())
		except RuntimeError, e:
			print >>sys.stderr, e
			return

		if args.action == 'list':
			print 'Name\t\tAdmin\tEmail\n----\t\t-----\t-----'
			print '\n'.join('{0: <16}{1}\t{2}'.format(u.name, '*' if u.admin else '', u.mail) for u in db.User.query.all())
		elif args.action == 'add':
			if not args.password:
				password = getpass.getpass()
				confirm  = getpass.getpass('Confirm password: ')
				if password != confirm:
					print >>sys.stderr, "Passwords don't match"
					return
				args.password = password
			status = UserManager.add(args.name, args.password, args.email, args.admin)
			if status != UserManager.SUCCESS:
				print >>sys.stderr, UserManager.error_str(status)
		elif args.action == 'delete':
			user = db.User.query.filter(db.User.name == args.name).first()
			if not user:
				print >>sys.stderr, 'No such user'
			else:
				db.session.delete(user)
				db.session.commit()
				print "User '{0.name}' deleted".format(args)
		elif args.action == 'set-admin':
			user = db.User.query.filter(db.User.name == args.name).first()
			if not user:
				print >>sys.stderr, 'No such user'
			else:
				user.admin = not args.off
				db.session.commit()
				print "{0} '{1}' admin rights".format('Revoked' if args.off else 'Granted', args.name)
		elif args.action == 'changepass':
			if not args.password:
				password = getpass.getpass()
				confirm  = getpass.getpass('Confirm password: ')
				if password != confirm:
					print >>sys.stderr, "Passwords don't match"
					return
				args.password = password
			status = UserManager.change_password2(args.name, args.password)
			if status != UserManager.SUCCESS:
				print >>sys.stderr, UserManager.error_str(status)
			else:
				print "Successfully changed '{}' password".format(args.name)

	def help_user(self):
		self.user_parser.print_help()

if __name__ == "__main__":
	if not config.check():
		sys.exit(1)

	import db
	db.init_db()

	from managers.folder import FolderManager
	from managers.user import UserManager
	from scanner import Scanner

	if len(sys.argv) > 1:
		CLI().onecmd(' '.join(sys.argv[1:]))
	else:
		CLI().cmdloop()


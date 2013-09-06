# coding: utf-8

import sys, cmd, argparse
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
			print >>sys.stderr, e.message
			return

		if args.action == 'list':
			print 'Name\t\tPath\n----\t\t----'
			print '\n'.join('%s\t\t%s' % (f.name, f.path) for f in db.Folder.query.filter(db.Folder.root == True))
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

if __name__ == "__main__":
	if not config.check():
		sys.exit(1)

	import db
	db.init_db()

	from managers.folder import FolderManager
	from scanner import Scanner

	if len(sys.argv) > 1:
		CLI().onecmd(' '.join(sys.argv[1:]))
	else:
		CLI().cmdloop()


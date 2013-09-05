# coding: utf-8

import sys, cmd
import config

class CLI(cmd.Cmd):
	prompt = "supysonic> "

	def do_EOF(self, line):
		return True

	def default(self, line):
		print 'Unknown command %s' % line.split()[0]
		self.do_help(None)

	def postloop(self):
		print

	def do_folder(self, line):
		action = line.split()[0] if line else 'list'
		args = line.split()[1:] if line else None

		if action == 'list':
			print 'Name\t\tPath\n----\t\t----'
			print '\n'.join('%s\t\t%s' % (f.name, f.path) for f in db.Folder.query.filter(db.Folder.root == True))
		elif action == 'add':
			if len(args) < 2:
				print 'Missing argument. folder add <name> <path>'
			else:
				ret = FolderManager.add(args[0], args[1])
				if ret != FolderManager.SUCCESS:
					print FolderManager.error_str(ret)
				else:
					print "Folder '%s' added" % args[0]
		elif action == 'delete':
			if len(args) < 1:
				print 'Missing argument. folder delete <name>'
			else:
				ret = FolderManager.delete_by_name(args[0])
				if ret != FolderManager.SUCCESS:
					print FolderManager.error_str(ret)
				else:
					print "Deleted folder '%s'" % args[0]
		else:
			print "Unknown action '%s'" % action

	def help_folder(self):
		print "folder\nfolder list\n\tDisplays the list of folders"
		print "folder add <name> <path>\n\tAdds a music folder <name> pointing to folder <path>"
		print "folder delete <name>\n\tDeletes folder <name>"

if __name__ == "__main__":
	if not config.check():
		sys.exit(1)

	import db
	db.init_db()

	from folder_manager import FolderManager

	if len(sys.argv) > 1:
		CLI().onecmd(' '.join(sys.argv[1:]))
	else:
		CLI().cmdloop()


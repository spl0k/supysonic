# coding: utf-8


import config
config.check()

from web import app
import db
from flask.ext.script import Manager, Command, Option, prompt_pass
import os.path
from managers.folder import FolderManager
from managers.user import UserManager
from scanner import Scanner

manager = Manager(app)

@manager.command
def folder_list():
    "Lists all Folders to Scan"
    print 'Name\t\tPath\n----\t\t----'
    print '\n'.join('{0: <16}{1}'.format(f.name, f.path) for f in db.Folder.query.filter(db.Folder.root == True))


@manager.command
def folder_add(name, path):
    "Add a folder to the Library"
    ret = FolderManager.add(path)
    if ret != FolderManager.SUCCESS:
        print FolderManager.error_str(ret)
    else:
        print "Folder '{}' added".format(name)

@manager.command
def folder_delete(path):
    "Delete folder from Library"

    s = Scanner(db.session)

    ret = FolderManager.delete_by_name(path, s)
    if ret != FolderManager.SUCCESS:
        print FolderManager.error_str(ret)
    else:
        print "Deleted folder" + path

@manager.command
def folder_scan():
    s = Scanner(db.session)

    folders = db.Folder.query.filter(db.Folder.root == True)

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
    s = Scanner(db.session)

    folders = db.Folder.query.filter(db.Folder.root == True)

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
    print '\n'.join('{0: <16}{1}\t{2}'.format(u.name, '*' if u.admin else '', u.mail) for u in db.User.query.all())

@manager.command
def user_add(name, admin=False, email=None):
    password = prompt_pass("Please enter a password")
    if password:
        status = UserManager.add(name, password, email, admin)
        if status != UserManager.SUCCESS:
            print >>sys.stderr, UserManager.error_str(status)

@manager.command
def user_delete(name):
    user = db.User.query.filter(db.User.name == name).first()
    if not user:
        print >>sys.stderr, 'No such user'
    else:
        db.session.delete(user)
        db.session.commit()
        print "User '{}' deleted".format(name)

@manager.command
def user_setadmin(name, off):
    user = db.User.query.filter(db.User.name == name).first()
    if not user:
        print >>sys.stderr, 'No such user'
    else:
        user.admin = not off
        db.session.commit()
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
def init_db():
    db.init_db()

@manager.command
def recreate_db():
    db.recreate_db()


if __name__ == "__main__":
    import config

    if not config.check():
        sys.exit(1)

    if not os.path.exists(config.get('base', 'cache_dir')):
        os.makedirs(config.get('base', 'cache_dir'))

    manager.run()

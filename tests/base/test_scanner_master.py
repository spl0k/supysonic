import os
import tempfile
import time
import unittest

from pony.orm import db_session
from supysonic import db
from supysonic import scanner_master
from supysonic.managers.folder import FolderManager

class ScannerMasterTestCase(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(prefix='supysonic-test-db-')
        db.init_database('sqlite:///%s'%self.db_file.name)

        with db_session:
            folder = FolderManager.add('folder', os.path.abspath('tests/assets'))
            self.assertIsNotNone(folder)
            self.folderid = folder.id
        self.master_connection_info = scanner_master.create_process()
        self.master = scanner_master.ScannerClient(self.master_connection_info)
        self.master.scan(str(folder.id))
        self.master.wait_for_finish()

    def tearDown(self):
        self.master.shutdown()
        db.release_database()
        self.db_file.close()
    
    def test_wait(self):
        self.assertFalse(self.master.status()[0])

    @db_session
    def test_scan(self):
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_status(self):
        # Only checks while inactive, unfortunately
        status = self.master.status()
        self.assertFalse(status[0])
        self.assertEqual(len(status), 1)

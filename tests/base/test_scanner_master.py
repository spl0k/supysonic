import os.path
import time
import unittest

from pony.orm import db_session
from supysonic import db
from supysonic import scanner_master
from supysonic.managers.folder import FolderManager

class ScannerMasterTestCase(unittest.TestCase):
    def setUp(self):
        db.init_database('sqlite:')

        with db_session:
            folder = FolderManager.add('folder', os.path.abspath('tests/assets'))
            self.assertIsNotNone(folder)
            self.folderid = folder.id
        self.master_connection_info = scanner_master.create_process()
        self.master = scanner_master.ScannerClient(self.master_connection_info)
        self.master.scan(folder.id)
        while self.master.status()[0]:
            time.sleep(0.05)

    def tearDown(self):
        db.release_database()
        self.master.shutdown()

    @db_session
    def test_scan(self):
        self.assertEqual(db.Track.select().count(), 1)

    @db_session
    def test_status(self):
        # Only checks while inactive, unfortunately
        status = self.master.status()
        self.assertFalse(status[0])
        self.assertEqual(status[1], -1)

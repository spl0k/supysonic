import multiprocessing
import secrets
import threading

from .managers.folder import FolderManager
from .scanner import Scanner
from pony.orm import db_session

def create_process():
    recv, send = multiprocessing.Pipe()
    process = multiprocessing.Process(target=set_up_in_process, args=(send,))
    process.start()
    connection_info = recv.recv()
    recv.close()
    return connection_info

def set_up_in_process(conn):
    authkey = secrets.token_bytes(8)
    listener = multiprocessing.connection.Listener(authkey=authkey)
    address = listener.address
    conn.send((address, authkey))

    sm = ScannerMaster(listener,[]) #TODO: Accept extensions
    sm.run()

class ScannerMaster():
    
    def __init__(self, listener, extensions):
        self.listener = listener
        self.extensions = extensions
        self.to_scan_condition = threading.Condition()
        self.to_scan = set()
        self.progress = -1
        self.scan_thread = threading.Thread(target=self._keep_scanning)
        self.shutting_down = False
        self.active_connections = set()
    
    def run(self):
        self.scan_thread.start()
        while not self.shutting_down:
            try:
                conn = self.listener.accept()
            except multiprocessing.connection.AuthenticationError:
                continue
            listen_thread = threading.Thread(target=self._listen_for_commands, args=(conn,))
            listen_thread.start()

    def shutdown(self, notify=None):
        self.shutting_down = True
        self.listener.close()
        for conn in self.active_connections:
            conn.close()
        self.to_scan_condition.acquire()
        self.to_scan_condition.notify_all()
        self.to_scan_condition.release()
        self.scan_thread.join()
        if notify:
            notify.send(None)

    def _keep_scanning(self):
        while not self.shutting_down:
            self.progress = -1
            self.to_scan_condition.acquire()
            while not len(self.to_scan):
                self.to_scan_condition.wait()
                if self.shutting_down:
                    self.to_scan_condition.release()
                    break
            folder = self.to_scan.pop()
            self.to_scan_condition.release()
            self._scan_folder(folder)

    def _scan_folder(self, folder_id):
        scanner = Scanner(extensions = self.extensions)
        with db_session:
            folder = FolderManager.get(folder_id) # TODO: Handle errors (Throws ValueError and ObjectNotFound)
            scanner.scan(folder, progress_callback=self._progress_callback) # TODO: Progress callbacks
            scanner.finish()
        stats = scanner.stats()
        if stats.errors:
            pass # TODO: Handle Errors

    def _progress_callback(self, progress):
        self.progress = progress
    
    def _listen_for_commands(self, conn):
        self.active_connections.add(conn)
        while not self.shutting_down:
            try:
                data = conn.recv()
            except EOFError:
                self.active_connections.remove(conn)
                break
            command = data[0].upper()
            args = data[1:]
            if command == 'SCAN':
                self.to_scan_condition.acquire()
                self.to_scan.add(args[0])
                self.to_scan_condition.notify()
                self.to_scan_condition.release()
            if command == 'STATUS':
                p = self.progress
                if p >= 0:
                    conn.send((True, p))
                else:
                    conn.send((False, ))
            elif command == 'SHUTDOWN':
                self.active_connections.remove(conn)
                self.shutdown(notify=conn)
                conn.close()

class ScannerClient():
    def __init__(self, connection_info):
        self.conn = multiprocessing.connection.Client(connection_info[0], authkey=connection_info[1])
    
    def scan(self, folder_id):
        self.conn.send(('SCAN', folder_id))

    def status(self):
        self.conn.send(('STATUS', ))
        return self.conn.recv()

    def shutdown(self):
        self.conn.send(('SHUTDOWN', ))
        self.conn.recv()

    def close(self):
        self.conn.close()

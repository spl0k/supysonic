import multiprocessing
import multiprocessing.connection
import os
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
    authkey = os.urandom(8)
    listener = multiprocessing.connection.Listener(authkey=authkey)
    address = listener.address
    conn.send((address, authkey))

    sm = ScannerMaster(listener,[]) #TODO: Accept extensions
    sm.run()

class ScannerMaster():
    
    def __init__(self, listener, extensions):
        self.listener = listener
        self.is_listening = False # Indicates that the listener thread has exited
        self.listener_thread_lock = threading.RLock() # For connecting to self.listener and read/writting self.is_listening
        self.extensions = extensions
        self.to_scan = set() # Folders queued to be scanned
        self.to_scan_condition = threading.Condition()
        self.progress = -1
        self.is_scanning = threading.Event()
        self.done_scanning = threading.Event()
        self.scan_thread = threading.Thread(target=self._keep_scanning)
        self.shutting_down = False
        self.shutdown_lock = threading.Lock()
        self.shutdown_complete = threading.Event()
        self.active_connections = set() # Active connections to `Client`s
    
    def run(self):
        self.listener_thread_lock.acquire()
        self.scan_thread.start()
        while not self.shutting_down:
            try:
                self.is_listening = True
                self.listener_thread_lock.release()
                conn = self.listener.accept()
                self.listener_thread_lock.acquire()
            except multiprocessing.connection.AuthenticationError:
                self.listener_thread_lock.acquire()
                continue
            except KeyboardInterrupt: # pragma: nocover
                self.listener_thread_lock.acquire()
                self.is_listening = False
                self.shutdown()
                break
            listen_thread = threading.Thread(target=self._listen_for_commands, args=(conn,))
            listen_thread.start()
        self.is_listening = False
        self.listener_thread_lock.release()

    def shutdown(self, notify=None):
        if self.shutdown_lock.acquire(False):
            self.shutting_down = True

            # Turn off the listener thread
            # Simply closing the listener doesn't cause the thread to stop
            # blocking, even though the listener can't be connected to.  The
            # solution to this is to
            #    1) Disable the loop in the listener thread, so that once it
            #       stops blocking, it exits
            #    2) Cause an error in the listener thread, so that it stops
            #       blocking
            #    3) Finally close the listener
            # However, if the listener thread has already stopped, for example
            # due to an interrrupt, we can just close the listener
            with self.listener_thread_lock:
                if self.is_listening:
                    try: # Do something to get the listener thread to stop blocking
                        conn = multiprocessing.connection.Client(self.listener.address, authkey=b'Some invalid key')
                    except multiprocessing.AuthenticationError:
                        pass
                self.listener.close()

            # Close all active connections
            # Because the listener is no longer active, we ca be assured that
            # there will be no more incomming connections, so there isn't a
            # lock for this part.  Note that the notify connection has
            # (hopefully) been removed from here already.  The blocking
            # connection threads will get a handleable exception, stop
            # blocking, and exit.
            for conn in self.active_connections:
                conn.close()

            # Close the scanner thread
            # If the scanner is currently awaiting a folder to scan, acquire
            # the Condition and notify the thread, so it wakes up and notices
            # that self.shutting_down has been set, causing it to exit.
            # If the scanner is currently scanning, this won't do anything, so
            # we just wait for it to finish scanning
            self.to_scan_condition.acquire()
            self.to_scan_condition.notify_all()
            self.to_scan_condition.release()
            self.scan_thread.join()

            # Finish shutting down and notify waiting connections
            self.shutdown_complete.set()
        self.shutdown_complete.wait()
        if notify:
            notify.send(None)

    def _keep_scanning(self):
        while not self.shutting_down:
            self.to_scan_condition.acquire()
            self.is_scanning.clear()
            self.progress = -1
            while not len(self.to_scan):
                self.done_scanning.set()
                self.to_scan_condition.wait()
                if self.shutting_down:
                    self.to_scan_condition.release()
                    break
            else:
                self.done_scanning.clear()
                folder = self.to_scan.pop()
                self.to_scan_condition.release()
                self._scan_folder(folder)

    def _scan_folder(self, folder_id):
        self.progress = 0
        self.is_scanning.set()
        scanner = Scanner(extensions = self.extensions)
        with db_session:
            folder = FolderManager.get(folder_id) # TODO: Handle errors (Throws ValueError and ObjectNotFound)
            scanner.scan(folder, progress_callback=self._progress_callback)
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
                self.to_scan |= set(args[0:])
                self.to_scan_condition.notify()
                self.to_scan_condition.release()
                is_scanning = self.is_scanning.wait(3)
                conn.send(is_scanning)
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
            elif command == 'WAIT':
                self.done_scanning.wait()
                conn.send(None)

class ScannerClient():
    def __init__(self, connection_info):
        self.conn = multiprocessing.connection.Client(connection_info[0], authkey=connection_info[1])
    
    def scan(self, *folder_ids):
        self.conn.send(('SCAN', ) + folder_ids)
        self.conn.recv()

    def status(self):
        self.conn.send(('STATUS', ))
        return self.conn.recv()

    def shutdown(self):
        self.conn.send(('SHUTDOWN', ))
        try:
            self.conn.recv()
        except EOFError: # pragma: nocover
            pass
   
    def wait_for_finish(self):
        self.conn.send(('WAIT',))
        try:
            self.conn.recv()
        except EOFError: # pragma: nocover
            pass

    def close(self):
        self.conn.close()

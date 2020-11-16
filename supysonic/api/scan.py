
from . import api
from functools import wraps
from flask import request
from flask import current_app
from .user import admin_only
from .exceptions import Forbidden,DaemonUnavailable,ServerError
from ..db import Folder
from ..daemon.client import DaemonClient
from ..daemon.exceptions import DaemonUnavailableError
from ..managers.folder import FolderManager

@api.route("/startScan.view", methods=["GET", "POST"])
@admin_only
def startScan():
    try:
        DaemonClient(current_app.config["DAEMON"]["socket"]).scan()
    except ValueError as e:
        ServerError(str(e))
    except DaemonUnavailableError:
        raise DaemonUnavailable()
    return getScanStatus()

@api.route("/getScanStatus.view", methods=["GET", "POST"])
@admin_only
def getScanStatus():
    try:
        scanned=DaemonClient(current_app.config["DAEMON"]["socket"]).get_scanning_progress()
    except DaemonUnavailableError:
        raise DaemonUnavailable()
    return request.formatter("scanStatus",
        dict(scanning='true' if scanned is not None else 'false',
            count= scanned if scanned is not None else 0))
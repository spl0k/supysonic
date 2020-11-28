from . import api
from flask import request
from flask import current_app
from .user import admin_only
from .exceptions import ServerError
from ..daemon.client import DaemonClient


@api.route("/startScan.view", methods=["GET", "POST"])
@admin_only
def startScan():
    try:
        daeomonclient = DaemonClient(current_app.config["DAEMON"]["socket"])
        daeomonclient.scan()
        scanned = daeomonclient.get_scanning_progress()
    except Exception as e:
        raise ServerError(str(e))
    return request.formatter(
        "scanStatus",
        dict(
            scanning="true" if scanned is not None else "false",
            count=scanned if scanned is not None else 0,
        ),
    )


@api.route("/getScanStatus.view", methods=["GET", "POST"])
@admin_only
def getScanStatus():
    try:
        scanned = DaemonClient(
            current_app.config["DAEMON"]["socket"]
        ).get_scanning_progress()
    except Exception as e:
        raise ServerError(str(e))
    return request.formatter(
        "scanStatus",
        dict(
            scanning="true" if scanned is not None else "false",
            count=scanned if scanned is not None else 0,
        ),
    )

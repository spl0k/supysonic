# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2019-2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import json
from dataclasses import asdict, dataclass, field
from typing import ClassVar
from uuid import UUID

from .exceptions import UnknownCommandError

__all__ = [
    "DaemonCommand",
    "WatcherCommand",
    "AddWatchedFolderCommand",
    "RemoveWatchedFolder",
    "ScannerCommand",
    "ScannerProgressCommand",
    "ScannerStartCommand",
    "JukeboxCommand",
    "StopCommand",
    "DaemonCommandResult",
    "ScannerProgressResult",
    "JukeboxResult",
    "encode",
    "decode",
]


class DaemonCommand:
    type: ClassVar[str]

    def to_wire(self):
        return asdict(self)


@dataclass
class StopCommand(DaemonCommand):
    type: ClassVar[str] = "stop"


@dataclass
class WatcherCommand(DaemonCommand):
    folder: str


class AddWatchedFolderCommand(WatcherCommand):
    type: ClassVar[str] = "add_watched_folder"


class RemoveWatchedFolder(WatcherCommand):
    type: ClassVar[str] = "remove_watched_folder"


class ScannerCommand(DaemonCommand):
    pass


@dataclass
class ScannerProgressCommand(ScannerCommand):
    type: ClassVar[str] = "scanner_progress"


@dataclass
class ScannerStartCommand(ScannerCommand):
    type: ClassVar[str] = "scanner_start"

    folders: list[str] = field(default_factory=list)
    force: bool = False


@dataclass
class JukeboxCommand(DaemonCommand):
    type: ClassVar[str] = "jukebox"

    action: str = ""
    args: list = field(default_factory=list)

    def to_wire(self):
        # UUIDs (set/add track ids) aren't JSON-native; send their canonical
        # string form. Peewee's UUIDField coerces it back on lookup.
        return {
            "action": self.action,
            "args": [str(a) if isinstance(a, UUID) else a for a in self.args],
        }


class DaemonCommandResult:
    type: ClassVar[str]

    def to_wire(self):
        return asdict(self)


@dataclass
class ScannerProgressResult(DaemonCommandResult):
    type: ClassVar[str] = "scanner_progress_result"

    scanned: int = None


@dataclass
class JukeboxResult(DaemonCommandResult):
    type: ClassVar[str] = "jukebox_result"

    playing: bool = False
    index: int = -1
    gain: float = 1.0
    position: int = 0
    playlist: list = field(default_factory=list)

    @classmethod
    def from_jukebox(cls, jukebox, playlist=None):
        if jukebox is None:
            return cls()
        return cls(
            playing=jukebox.playing,
            index=jukebox.index,
            gain=jukebox.gain,
            position=jukebox.position,
            playlist=list(playlist) if playlist is not None else [],
        )


_REGISTRY = {
    c.type: c
    for c in (
        AddWatchedFolderCommand,
        RemoveWatchedFolder,
        ScannerProgressCommand,
        ScannerStartCommand,
        JukeboxCommand,
        StopCommand,
        ScannerProgressResult,
        JukeboxResult,
    )
}


def encode(msg):
    return json.dumps({"type": msg.type, **msg.to_wire()}).encode()


def decode(raw):
    data = json.loads(raw)  # JSONDecodeError on non-JSON payloads
    tag = data.pop("type", None)
    cls = _REGISTRY.get(tag)
    if cls is None:
        raise UnknownCommandError(tag)
    return cls(**data)

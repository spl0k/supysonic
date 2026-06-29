# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2026 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

# Cross-platform stand-ins for the Unix command-line tools (echo, dd, cat,
# md5sum) used as fake transcoders by the test suite. Invoked through
# sys.executable so the transcoding tests can run on Windows as well.

import hashlib
import os
import sys


def main():
    out = sys.stdout.buffer
    cmd, *rest = sys.argv[1:]

    if cmd == "echo":  # echo -n a b
        out.write(" ".join(rest).encode())
    elif cmd == "urandom":  # dd if=/dev/urandom ...
        out.write(os.urandom(int(rest[0])))
    elif cmd == "decode":  # echo -n "Pushing out some mp3 data..."
        out.write(b"Pushing out some mp3 data...")
    elif cmd == "cat":  # cat -
        out.write(sys.stdin.buffer.read())
    elif cmd == "md5":  # md5sum
        out.write(hashlib.md5(sys.stdin.buffer.read()).hexdigest().encode())
    else:
        raise SystemExit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()

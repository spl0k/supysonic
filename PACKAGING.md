# Packaging Notes

Notes for distro package maintainers.

## Source archive

The source distribution published on PyPI only contains what the Python build
needs: neither the `docs/` folder nor `config.sample` are part of it. Packages
that ship man pages or the configuration sample must be built from the source
archive of the release's git tag (e.g. the GitHub tarball).

## Man pages

Man pages are not included in the PyPI distribution, nor installed by the
wheel. They must be built from the Sphinx sources in `docs/` using the `man`
builder:

```
sphinx-build -b man docs <destdir>
```

This produces five section-1 pages, to be installed under `/usr/share/man/man1/`:

| File | Description |
|---|---|
| `supysonic-cli.1` | Management command-line interface |
| `supysonic-cli-user.1` | User management sub-commands |
| `supysonic-cli-folder.1` | Folder management sub-commands |
| `supysonic-daemon.1` | Background daemon |
| `supysonic-server.1` | Standalone web server |

`sphinx` must be available at build time. No other Sphinx extensions are required,
and Supysonic doesn't need to be installed: the build imports it from the source
tree and mocks its dependencies.

## Configuration sample

A sample configuration file is provided at `config.sample` in the repository
root (not in the PyPI distribution). It is not installed by the Python build.
The conventional install path is:

```
/usr/share/doc/supysonic/config.sample
```

Users copy it to one of the locations Supysonic searches at startup:

- `/etc/supysonic` (system-wide)
- `~/.supysonic` (user, short form)
- `~/.config/supysonic/supysonic.conf` (user, XDG-style)
- `supysonic.conf` (current working directory)

## Entry-point scripts

Three console scripts are declared in `pyproject.toml`:

| Script | Purpose |
|---|---|
| `supysonic-cli` | Administrative CLI (library management, user management, …) |
| `supysonic-daemon` | Optional background daemon (file watcher, jukebox, background scans) |
| `supysonic-server` | Built-in WSGI server (development / simple deployments) |

### systemd unit for the daemon

The daemon (`supysonic-daemon`) is a long-running process suitable for a
systemd service. A minimal unit file:

```ini
[Unit]
Description=Supysonic Daemon

[Service]
User=supysonic
Group=supysonic
ExecStart=/usr/bin/supysonic-daemon

[Install]
WantedBy=multi-user.target
```

See the [daemon documentation](https://supysonic.readthedocs.io/en/latest/setup/daemon.html).

## Upgrades

- Database migrations are applied automatically when Supysonic starts; no
  maintainer script needs to run them.
- The web application and the daemon communicate through a private protocol
  that may change between versions: on upgrade, restart both so they run the
  same version.

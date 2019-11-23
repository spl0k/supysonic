# Jukebox

The jukebox mode allow playing audio files on the hardware of the machine
running Supysonic, using regular clients that support it as a remote control.

The daemon must be running in order to be able to use the jukebox mode. So be
sure to start the `supysonic-daemon` command and keep it running. A basic
_systemd_ service file can be found at the root of the project folder.

## Setting the player program

Jukebox mode in _Supysonic_ works through the use of third-party command-line
programs. _Supysonic_ isn't bundled with such programs, and you are left to
choose which one you want to use. The chosen program should be able to play a
single audio file from a path specified on its command-line.

The configuration is done in the `[daemon]` section of the
[configuration file](configuration.md), with the `jukebox_command` variable.
This variable should include the following fields:

- `%path`: absolute path of the file to be played
- `%offset`: time in seconds where to start playing (used for seeking)

Here's an example using `mplayer`:
```
jukebox_command = mplayer -ss %offset %path
```

Or using `mpv`:
```
jukebox_command = mpv --start=%offset %path
```

Setting the output volume isn't currently supported.

## Allowing users to act on the jukebox

The jukebox mode is only accessible to chosen users. Granting (or revoking)
jukebox usage rights to a specific user is done with the [CLI](cli.md):

```
$ supysonic-cli user setroles --jukebox <username>
```

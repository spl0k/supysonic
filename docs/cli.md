# Command line interface

The command-line interface (often abbreviated CLI) is an interface allowing
administration operations without the use of the web interface. It can either
be run in interactive mode (`supysonic-cli`) or to issue a single command
(`supysonic-cli <arguments>`).

If ran without arguments, `supysonic-cli` will open an interactive prompt. You
can use the command line tool to do a few things:

## Help commands

Whenever you are lost

```
Usage:
    supysonic-cli help
    supysonic-cli help user
    supysonic-cli help folder

Arguments:
    user                        Display the help message for the user command
    folder                      Display the help message for the folder command
```

## User management commands

```
Usage:
    supysonic-cli user add <user> [-p <password>] [-e <email>]
    supysonic-cli user delete <user>
    supysonic-cli user changepass <user> <password>
    supysonic-cli user list
    supysonic-cli user setroles [-a|-A] [-j|-J] <user>

Arguments:
    add                         Add a new user
    delete                      Delete the user
    changepass                  Change the user's password
    list                        List all the users
    setroles                    Give or remove rights to the user

Options:
  -p --password <password>      Specify the user's password
  -e --email <email>            Specify the user's email
  -a --noadmin                  Revoke admin rights
  -A --admin                    Grant admin rights
  -j --nojukebox                Revoke jukebox rights
  -J --jukebox                  Grant jukebox rights
```

## Folder management commands

```
Usage:
    supysonic-cli folder add <name> <path>
    supysonic-cli folder delete <name>
    supysonic-cli folder list
    supysonic-cli folder scan [-f] [--background | --foreground] [<name>...]

Arguments:
    add                         Add a new folder
    delete                      Delete a folder
    list                        List all the folders
    scan                        Scan all or specified folders

Options:
  -f --force                    Force scan of already known files even if they
                                haven't changed
  --background                  Scan in the background. Requires the daemon to
                                be running.
  --foreground                  Scan in the foreground, blocking the process
                                while the scan is running
```

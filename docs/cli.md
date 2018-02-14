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
    supysonic-cli user add <user> [-a] [-p <password>] [-e <email>]
    supysonic-cli user delete <user>
    supysonic-cli user changepass <user> <password>
    supysonic-cli user list
    supysonic-cli user setadmin [--off] <user>

Arguments:
    add                         Add a new user
    delete                      Delete the user
    changepass                  Change the user's password
    list                        List all the users
    setadmin                    Give admin rights to the user

Options:
  -a --admin                    Create the user with admin rights
  -p --password <password>      Specify the user's password
  -e --email <email>            Specify the user's email
  --off                         Revoke the admin rights if present
```

## Folder management commands

```
Usage:
    supysonic-cli folder add <name> <path>
    supysonic-cli folder delete <name>
    supysonic-cli folder list
    supysonic-cli folder scan [<name>...]

Arguments:
    add                         Add a new folder
    delete                      Delete a folder
    list                        List all the folders
    scan                        Scan all or specified folders
```


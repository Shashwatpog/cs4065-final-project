# Project 2 - Bulletin Board System

## Overview

This is the programming assignment 2 for CS4065: Computer Networks 

- `server.py` : multi threaded TCP server
- `client_cli.py` : command-line client with all required commands
- `client_gui.py` : tkinter GUI client 

---

## How to Run

### Requirements

- Python 3.8+
- Standard library only (no extra packages, Tkinter is included in the python standard library for GUI)

### Server

First run the server 

```bash
# default port 12345
python3 server.py

# or specify port
python3 server.py 5555
```

Then you can either run the CLI or the GUI client using the following

### Client Command Line Interface (CLI)

```bash 
python3 client_cli.py
```

Once it starts, type commands prefixed with `%`. Start by connecting and picking a username when prompted:

```text
%connect 127.0.0.1 12345
# prompted for a username; type something unique
```

After connecting you can use:
- `%join` : join the public board.
- `%post <subject> <body...>` : post to the public board.
- `%users` : list users in the current public board.
- `%leave` : leave the public board.
- `%message <id>` : fetch a specific public message.
- `%groups` : list available groups.
- `%groupjoin <group>` : join a named group.
- `%grouppost <group> <subject> <body...>` : post to a specific group.
- `%groupusers <group>` : list users in a group.
- `%groupleave <group>` : leave a group.
- `%groupmessage <group> <id>` : fetch a specific group message.
- `%help` : show the command list.
- `%exit` : close the client (sends an exit to the server if connected).

### Client Graphic User Interface (GUI)

```bash
python3 client_gui.py
```



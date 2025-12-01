# Project 2 - Bulletin Board System

## Overview

This is the programming assignment 2 for CS4065: Computer Networks 

Bulletin-board system where clients connect to a TCP server, choose a username, and post/read messages in a public board or named groups. Includes both CLI and GUI clients for interacting with the server.

- `server.py` : multi threaded TCP server
- `client_cli.py` : command-line client with all required commands
- `client_gui.py` : tkinter GUI client 

### Features
- **Public Message Board:** Send messages, view active users, and retrieve specific messages
- **Private Message Boards:** Join rooms, send messages, and manage room interactions
- **GUI:** User-friendly interface with separate sections for command feedback and chat messages

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
```

After connecting you can use:

| Command | Description | Example
| --- | --- | --- |
| `%connect <host> <port>` | Connect to the server | %connect 127.0.0.1 12345 |
| `%join` | Join the public board | %join |
| `%post <subject> <body>` | Post to the public board | %post Hi Hi this is a test message |
| `%users` | List users in the current public board | |
| `%leave` | Leave the public board | |
| `%message <id>` | Fetch a specific public message | %message 12 |
| `%groups` | List available groups | |
| `%groupjoin <group>` | Join a named group | %groupjoin group5 |
| `%grouppost <group> <subject> <body>` | Post to a specific group | %grouppost group5 Hi Hi this is a test |
| `%groupusers <group>` | List users in a group | |
| `%groupleave <group>` | Leave a group | |
| `%groupmessage <group> <id>` | Fetch a specific group message | %groupmessage group5 12 |
| `%help` | Show the command list | |
| `%exit` | Close the client (sends an exit to the server if connected) | |
| `%shutdown` | Ask the server to shut down | |

### Client Graphic User Interface (GUI)

```bash
python3 client_gui.py
```



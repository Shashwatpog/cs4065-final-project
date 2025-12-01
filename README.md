# Project 2 - Simple Bulletin Board Using Socket Programming

## Overview

This project implements a **bulletin board system** using **pure TCP sockets** in Python.

- `server.py` – Multithreaded TCP server
- `client_cli.py` – Command-line client with all required commands
- `client_gui.py` – Tkinter GUI client 

---

## How to Run

### Requirements

- Python 3.8+
- Standard library only (no extra packages, Tkinter is included in the python standard library for GUI)

### Server

```bash
# default port 12345
python3 server.py

# or specify port
python3 server.py 5555
```

### Client Command Line Interface (CLI)

```bash 
python3 client_cli.py
```

### Client Graphic User Interface (GUI)

```bash
python3 client_gui.py
```



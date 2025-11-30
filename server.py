#!/usr/bin/env python3
import socket
import threading
import json
import sys
from datetime import datetime

DEFAULT_PORT = 12345

class ClientInfo:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.username = None
        self.groups = set()
        self.send_lock = threading.Lock()

    def __repr__(self):
        return f"<Client {self.username}@{self.addr}>"

# Global server state
clients_lock = threading.Lock()
clients = set()  # set of ClientInfo
username_to_client = {}

state_lock = threading.Lock()
groups = {}  # group_name -> {"members": set(usernames), "messages": [msg_dict]}
next_msg_id = 1

# Predefined groups for Part 2
PREDEFINED_GROUPS = ["group1", "group2", "group3", "group4", "group5"]
PUBLIC_GROUP = "public"

# Shutdown control
server_stop_event = threading.Event()


def init_groups():
    with state_lock:
        groups.clear()
        # public board (Part 1)
        groups[PUBLIC_GROUP] = {"members": set(), "messages": []}
        # private groups (Part 2)
        for g in PREDEFINED_GROUPS:
            groups[g] = {"members": set(), "messages": []}


def send_json(client: ClientInfo, obj: dict):
    try:
        data = (json.dumps(obj) + "\n").encode("utf-8")
        with client.send_lock:
            client.sock.sendall(data)
    except OSError:
        # socket likely closed
        pass


def broadcast_event(group_name: str, event: dict, exclude_username=None):
    """
    Send an event to all users in a given group.
    event should already include {"type": "event", ...}
    """
    with state_lock:
        members = list(groups.get(group_name, {}).get("members", []))
    targets = []
    with clients_lock:
        for uname in members:
            if exclude_username and uname == exclude_username:
                continue
            client = username_to_client.get(uname)
            if client:
                targets.append(client)
    for c in targets:
        send_json(c, event)


def handle_set_username(client, data):
    username = data.get("username")
    if not username:
        send_json(client, {"type": "error", "message": "Username is required"})
        return
    with clients_lock:
        if username in username_to_client:
            send_json(client, {"type": "error", "message": "Username already taken"})
            return
        # accept username
        client.username = username
        username_to_client[username] = client
    send_json(client, {
        "type": "info",
        "subtype": "username_accepted",
        "message": f"Username {username} accepted"
    })
    # Immediately send list of available groups (Part 2 requirement)
    handle_groups(client, {})


def handle_join(client, data):
    group = data.get("group", PUBLIC_GROUP)
    if group not in groups:
        send_json(client, {"type": "error", "message": f"Unknown group: {group}"})
        return
    if client.username is None:
        send_json(client, {"type": "error", "message": "Set username first"})
        return

    with state_lock:
        groups[group]["members"].add(client.username)
        client.groups.add(group)
        # last 2 messages
        history_msgs = groups[group]["messages"][-2:]

    # send history to this user
    send_json(client, {
        "type": "history",
        "group": group,
        "messages": history_msgs
    })

    # send users list (including self)
    handle_users(client, {"group": group})

    # notify others in group
    event = {
        "type": "event",
        "event": "user_joined",
        "group": group,
        "user": client.username
    }
    broadcast_event(group, event, exclude_username=client.username)


def handle_post(client, data):
    global next_msg_id
    group = data.get("group", PUBLIC_GROUP)
    subject = data.get("subject", "")
    body = data.get("body", "")

    if client.username is None:
        send_json(client, {"type": "error", "message": "Set username first"})
        return
    if group not in groups:
        send_json(client, {"type": "error", "message": f"Unknown group: {group}"})
        return
    if group not in client.groups:
        send_json(client, {"type": "error", "message": f"You are not in group {group}"})
        return

    timestamp = datetime.now().isoformat(timespec="seconds")
    with state_lock:
        msg_id = next_msg_id
        next_msg_id += 1
        msg = {
            "id": msg_id,
            "sender": client.username,
            "group": group,
            "subject": subject,
            "body": body,
            "timestamp": timestamp
        }
        groups[group]["messages"].append(msg)

    # Broadcast a summary of the new message
    event = {
        "type": "event",
        "event": "new_message",
        "group": group,
        "id": msg_id,
        "sender": client.username,
        "subject": subject,
        "date": timestamp
    }
    broadcast_event(group, event)


def handle_users(client, data):
    group = data.get("group", PUBLIC_GROUP)
    if group not in groups:
        send_json(client, {"type": "error", "message": f"Unknown group: {group}"})
        return
    with state_lock:
        user_list = sorted(groups[group]["members"])
    send_json(client, {
        "type": "response",
        "command": "users",
        "group": group,
        "users": user_list
    })


def handle_groups(client, data):
    with state_lock:
        all_groups = sorted(groups.keys())
    send_json(client, {
        "type": "response",
        "command": "groups",
        "groups": all_groups
    })


def handle_leave(client, data):
    group = data.get("group", PUBLIC_GROUP)
    if group not in groups:
        send_json(client, {"type": "error", "message": f"Unknown group: {group}"})
        return
    if client.username is None:
        return
    with state_lock:
        if client.username in groups[group]["members"]:
            groups[group]["members"].remove(client.username)
        if group in client.groups:
            client.groups.remove(group)
    event = {
        "type": "event",
        "event": "user_left",
        "group": group,
        "user": client.username
    }
    broadcast_event(group, event, exclude_username=client.username)


def handle_get_message(client, data):
    group = data.get("group", PUBLIC_GROUP)
    msg_id = data.get("id")
    if group not in groups:
        send_json(client, {"type": "error", "message": f"Unknown group: {group}"})
        return
    if msg_id is None:
        send_json(client, {"type": "error", "message": "Message ID required"})
        return
    with state_lock:
        messages = groups[group]["messages"]
        found = None
        for m in messages:
            if m["id"] == msg_id:
                found = m
                break
    if not found:
        send_json(client, {"type": "error", "message": f"No message with ID {msg_id} in group {group}"})
        return
    send_json(client, {
        "type": "response",
        "command": "message",
        "group": group,
        "message": found
    })


def disconnect_client(client: ClientInfo):
    # Remove from groups and global lists
    with clients_lock:
        if client in clients:
            clients.remove(client)
        if client.username and username_to_client.get(client.username) == client:
            del username_to_client[client.username]

    # Broadcast user_left for each group they were in
    if client.username:
        with state_lock:
            groups_and_members = list(groups.items())
        for gname, gdata in groups_and_members:
            with state_lock:
                if client.username in gdata["members"]:
                    gdata["members"].remove(client.username)
            event = {
                "type": "event",
                "event": "user_left",
                "group": gname,
                "user": client.username
            }
            broadcast_event(gname, event, exclude_username=client.username)

    try:
        client.sock.close()
    except OSError:
        pass
    print(f"Client disconnected: {client.addr} ({client.username})")


def handle_client(client: ClientInfo):
    sock = client.sock
    addr = client.addr
    print(f"New connection from {addr}")
    # Welcome message
    send_json(client, {
        "type": "info",
        "message": "Welcome to the Bulletin Board. Please set your username."
    })
    f = sock.makefile("r")
    try:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                send_json(client, {"type": "error", "message": "Invalid JSON"})
                continue
            action = data.get("action")
            if not action:
                send_json(client, {"type": "error", "message": "Missing action"})
                continue

            if action == "set_username":
                handle_set_username(client, data)
            elif action == "join":
                handle_join(client, data)
            elif action == "post":
                handle_post(client, data)
            elif action == "users":
                handle_users(client, data)
            elif action == "groups":
                handle_groups(client, data)
            elif action == "leave":
                handle_leave(client, data)
            elif action == "get_message":
                # ensure msg id is int if it came as string
                if "id" in data and isinstance(data["id"], str):
                    try:
                        data["id"] = int(data["id"])
                    except ValueError:
                        pass
                handle_get_message(client, data)
            elif action == "exit":
                break
            elif action == "shutdown":
                # Remote shutdown command (extra convenience)
                print(f"Shutdown requested by {client.username} from {client.addr}")
                send_json(client, {"type": "info", "message": "Server shutting down."})
                server_stop_event.set()
                break
            else:
                send_json(client, {"type": "error", "message": f"Unknown action: {action}"})
    except Exception as e:
        print(f"Error with client {addr}: {e}")
    finally:
        disconnect_client(client)


def run_server(port: int):
    init_groups()
    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv_sock.bind(("0.0.0.0", port))
    srv_sock.listen()
    # IMPORTANT: timeout so Ctrl+C works on Windows while accept() is blocking
    srv_sock.settimeout(1.0)

    print(f"Server listening on port {port}... (Ctrl+C to stop)")

    try:
        while not server_stop_event.is_set():
            try:
                client_sock, addr = srv_sock.accept()
            except socket.timeout:
                # Just loop again, allowing KeyboardInterrupt or shutdown event to be processed
                continue

            client = ClientInfo(client_sock, addr)
            with clients_lock:
                clients.add(client)
            t = threading.Thread(target=handle_client, args=(client,), daemon=True)
            t.start()

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received, shutting down server...")
        server_stop_event.set()
    finally:
        print("Closing listening socket...")
        try:
            srv_sock.close()
        except OSError:
            pass

        # Disconnect all clients
        with clients_lock:
            current_clients = list(clients)
        for c in current_clients:
            disconnect_client(c)

        print("Server stopped.")


if __name__ == "__main__":
    port = DEFAULT_PORT
    if len(sys.argv) >= 2:
        port = int(sys.argv[1])
    run_server(port)

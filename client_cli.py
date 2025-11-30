#!/usr/bin/env python3
import socket
import json
import threading
import sys

sock = None
sock_file = None
receiver_thread = None
connected = False
current_username = None
lock = threading.Lock()

def send_obj(obj):
    global sock
    if not sock:
        print("Not connected.")
        return
    data = (json.dumps(obj) + "\n").encode("utf-8")
    with lock:
        sock.sendall(data)

def handle_server_message(obj):
    t = obj.get("type")
    if t == "info":
        msg = obj.get("message", "")
        subtype = obj.get("subtype")
        print(f"[INFO] {msg}")
        if subtype == "username_accepted":
            global current_username
            # We don't know the username from here,
            # but it's okay; we already know it client-side.
    elif t == "error":
        print(f"[ERROR] {obj.get('message','')}")
    elif t == "event":
        ev = obj.get("event")
        if ev == "user_joined":
            print(f"[EVENT] {obj.get('user')} joined group {obj.get('group')}")
        elif ev == "user_left":
            print(f"[EVENT] {obj.get('user')} left group {obj.get('group')}")
        elif ev == "new_message":
            print(f"[NEW MESSAGE] ({obj.get('group')}) "
                  f"ID={obj.get('id')} From={obj.get('sender')} "
                  f"Date={obj.get('date')} Subject={obj.get('subject')}")
        else:
            print(f"[EVENT] {obj}")
    elif t == "response":
        cmd = obj.get("command")
        if cmd == "groups":
            print("[GROUPS] Available groups:")
            for g in obj.get("groups", []):
                print(f"  - {g}")
        elif cmd == "users":
            group = obj.get("group")
            users = obj.get("users", [])
            print(f"[USERS in {group}] {', '.join(users) if users else '(none)'}")
        elif cmd == "message":
            group = obj.get("group")
            m = obj.get("message", {})
            print(f"[MESSAGE {m.get('id')} in {group}]")
            print(f" From: {m.get('sender')}")
            print(f" Date: {m.get('timestamp')}")
            print(f" Subject: {m.get('subject')}")
            print(" Body:")
            print(m.get("body", ""))
        else:
            print(f"[RESPONSE] {obj}")
    elif t == "history":
        group = obj.get("group")
        msgs = obj.get("messages", [])
        print(f"[HISTORY for {group}] (last {len(msgs)} messages)")
        for m in msgs:
            print(f"  ID={m.get('id')} From={m.get('sender')} "
                  f"Date={m.get('timestamp')} Subject={m.get('subject')}")
    else:
        print(f"[SERVER] {obj}")

def receiver_loop():
    global sock_file, connected
    try:
        for line in sock_file:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                handle_server_message(obj)
            except json.JSONDecodeError:
                print("[CLIENT] Invalid JSON from server:", line)
    except Exception as e:
        if connected:
            print("[CLIENT] Connection error:", e)
    finally:
        connected = False
        print("[CLIENT] Disconnected from server.")

def connect_cmd(host, port):
    global sock, sock_file, receiver_thread, connected, current_username
    if connected:
        print("Already connected. Use %exit to disconnect first.")
        return

    # 1) connect socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    f = s.makefile("r")
    sock = s
    sock_file = f
    connected = True
    print(f"Connected to {host}:{port}")

    # 2) read and handle the initial WELCOME message from server (if any)
    try:
        first = f.readline()
        if first:
            first = first.strip()
            if first:
                try:
                    obj = json.loads(first)
                    handle_server_message(obj)
                except json.JSONDecodeError:
                    print("[CLIENT] Invalid JSON during welcome:", first)
    except Exception as e:
        print("[CLIENT] Error reading welcome from server:", e)
        connected = False
        sock.close()
        return

    # 3) Handshake for username (only look at responses to set_username)
    while True:
        username = input("Enter a username: ").strip()
        if not username:
            continue

        send_obj({"action": "set_username", "username": username})

        # loop until we see either an error or username_accepted
        while True:
            line = f.readline()
            if not line:
                print("Server closed connection during username handshake.")
                connected = False
                sock.close()
                return

            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                print("[CLIENT] Invalid JSON during handshake:", line)
                continue

            # If it's an error, show it and go back to ask for username again
            if obj.get("type") == "error":
                handle_server_message(obj)
                # break inner loop -> ask username again
                break

            # Handle informational / other responses (e.g., groups)
            handle_server_message(obj)

            # Username accepted?
            if obj.get("type") == "info" and obj.get("subtype") == "username_accepted":
                current_username = username
                # break out of BOTH loops
                username_accepted = True
                break
        else:
            # shouldn't hit this; just in case
            continue

        # Did we accept the username? if yes, fall out of outer while
        if 'username_accepted' in locals() and username_accepted:
            break

    # 4) Start receiver thread AFTER username is finalized
    receiver_thread = threading.Thread(target=receiver_loop, daemon=True)
    receiver_thread.start()
    print("You can now use %join, %groups, %post, etc. Type %help for commands.")


def print_help():
    print("Commands:")
    print("  %connect <host> <port>")
    print("  %join                     (join public board)")
    print("  %post <subject> <body...>")
    print("  %users")
    print("  %leave")
    print("  %message <id>")
    print("  %groups")
    print("  %groupjoin <group>")
    print("  %grouppost <group> <subject> <body...>")
    print("  %groupusers <group>")
    print("  %groupleave <group>")
    print("  %groupmessage <group> <id>")
    print("  %help")
    print("  %exit")

def main_loop():
    global connected, sock, sock_file
    print("Simple Bulletin Board Client (CLI)")
    print("Type %help for available commands.")
    while True:
        try:
            cmd = input("> ").strip()
        except EOFError:
            cmd = "%exit"
        if not cmd:
            continue
        if not cmd.startswith("%"):
            print("Commands must start with %. Type %help.")
            continue
        parts = cmd.split()
        name = parts[0].lower()

        if name == "%help":
            print_help()

        elif name == "%connect":
            if len(parts) != 3:
                print("Usage: %connect <host> <port>")
                continue
            host = parts[1]
            try:
                port = int(parts[2])
            except ValueError:
                print("Port must be an integer.")
                continue
            connect_cmd(host, port)

        elif name == "%join":
            if not connected:
                print("Not connected.")
                continue
            send_obj({"action": "join", "group": "public"})

        elif name == "%post":
            if not connected:
                print("Not connected.")
                continue
            if len(parts) < 3:
                print("Usage: %post <subject> <body...>")
                continue
            subject = parts[1]
            body = " ".join(parts[2:])
            send_obj({"action": "post", "group": "public", "subject": subject, "body": body})

        elif name == "%users":
            if not connected:
                print("Not connected.")
                continue
            send_obj({"action": "users", "group": "public"})

        elif name == "%leave":
            if not connected:
                print("Not connected.")
                continue
            send_obj({"action": "leave", "group": "public"})

        elif name == "%message":
            if not connected:
                print("Not connected.")
                continue
            if len(parts) != 2:
                print("Usage: %message <id>")
                continue
            try:
                mid = int(parts[1])
            except ValueError:
                print("ID must be an integer.")
                continue
            send_obj({"action": "get_message", "group": "public", "id": mid})

        elif name == "%groups":
            if not connected:
                print("Not connected.")
                continue
            send_obj({"action": "groups"})

        elif name == "%groupjoin":
            if not connected:
                print("Not connected.")
                continue
            if len(parts) != 2:
                print("Usage: %groupjoin <group>")
                continue
            group = parts[1]
            send_obj({"action": "join", "group": group})

        elif name == "%grouppost":
            if not connected:
                print("Not connected.")
                continue
            if len(parts) < 4:
                print("Usage: %grouppost <group> <subject> <body...>")
                continue
            group = parts[1]
            subject = parts[2]
            body = " ".join(parts[3:])
            send_obj({"action": "post", "group": group, "subject": subject, "body": body})

        elif name == "%groupusers":
            if not connected:
                print("Not connected.")
                continue
            if len(parts) != 2:
                print("Usage: %groupusers <group>")
                continue
            group = parts[1]
            send_obj({"action": "users", "group": group})

        elif name == "%groupleave":
            if not connected:
                print("Not connected.")
                continue
            if len(parts) != 2:
                print("Usage: %groupleave <group>")
                continue
            group = parts[1]
            send_obj({"action": "leave", "group": group})

        elif name == "%groupmessage":
            if not connected:
                print("Not connected.")
                continue
            if len(parts) != 3:
                print("Usage: %groupmessage <group> <id>")
                continue
            group = parts[1]
            try:
                mid = int(parts[2])
            except ValueError:
                print("ID must be an integer.")
                continue
            send_obj({"action": "get_message", "group": group, "id": mid})

        elif name == "%exit":
            if connected:
                try:
                    send_obj({"action": "exit"})
                except Exception:
                    pass
                try:
                    sock.close()
                except Exception:
                    pass
                connected = False
            print("Exiting client.")
            break
        elif name == "%shutdown":
            if not connected:
                print("Not connected.")
                continue
            send_obj({"action": "shutdown"})
            
        else:
            print("Unknown command. Type %help.")

if __name__ == "__main__":
    main_loop()

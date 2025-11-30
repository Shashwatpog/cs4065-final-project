#!/usr/bin/env python3
import tkinter as tk
from tkinter import scrolledtext, messagebox
import socket
import json
import threading

class GuiClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Bulletin Board Client (GUI)")
        self.sock = None
        self.sock_file = None
        self.connected = False
        self.send_lock = threading.Lock()

        self.build_ui()

    def build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(top, text="Host:").grid(row=0, column=0, sticky="w")
        self.host_entry = tk.Entry(top, width=15)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.grid(row=0, column=1)

        tk.Label(top, text="Port:").grid(row=0, column=2, sticky="w")
        self.port_entry = tk.Entry(top, width=6)
        self.port_entry.insert(0, "12345")
        self.port_entry.grid(row=0, column=3)

        tk.Label(top, text="Username:").grid(row=0, column=4, sticky="w")
        self.user_entry = tk.Entry(top, width=12)
        self.user_entry.grid(row=0, column=5)

        self.connect_btn = tk.Button(top, text="Connect", command=self.connect)
        self.connect_btn.grid(row=0, column=6, padx=5)

        self.groups_btn = tk.Button(top, text="Get Groups", command=self.get_groups, state=tk.DISABLED)
        self.groups_btn.grid(row=0, column=7, padx=5)

        # Group and message controls
        mid = tk.Frame(self.root)
        mid.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(mid, text="Group:").grid(row=0, column=0, sticky="w")
        self.group_entry = tk.Entry(mid, width=10)
        self.group_entry.insert(0, "public")
        self.group_entry.grid(row=0, column=1)

        self.join_btn = tk.Button(mid, text="Join Group", command=self.join_group, state=tk.DISABLED)
        self.join_btn.grid(row=0, column=2, padx=3)

        self.users_btn = tk.Button(mid, text="Group Users", command=self.group_users, state=tk.DISABLED)
        self.users_btn.grid(row=0, column=3, padx=3)

        self.leave_btn = tk.Button(mid, text="Leave Group", command=self.leave_group, state=tk.DISABLED)
        self.leave_btn.grid(row=0, column=4, padx=3)

        # Subject + Body
        msg_frame = tk.Frame(self.root)
        msg_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(msg_frame, text="Subject:").grid(row=0, column=0, sticky="w")
        self.subject_entry = tk.Entry(msg_frame, width=30)
        self.subject_entry.grid(row=0, column=1, columnspan=3, sticky="we")

        tk.Label(msg_frame, text="Body:").grid(row=1, column=0, sticky="nw")
        self.body_text = tk.Text(msg_frame, height=4, width=50)
        self.body_text.grid(row=1, column=1, columnspan=3, sticky="we")

        self.post_btn = tk.Button(msg_frame, text="Post", command=self.post_message, state=tk.DISABLED)
        self.post_btn.grid(row=1, column=4, padx=3, sticky="n")

        # Message retrieval
        tk.Label(msg_frame, text="Msg ID:").grid(row=2, column=0, sticky="w")
        self.msgid_entry = tk.Entry(msg_frame, width=6)
        self.msgid_entry.grid(row=2, column=1, sticky="w")
        self.getmsg_btn = tk.Button(msg_frame, text="Get Message", command=self.get_message, state=tk.DISABLED)
        self.getmsg_btn.grid(row=2, column=2, padx=3, sticky="w")

        # Log area
        self.log = scrolledtext.ScrolledText(self.root, height=18, width=80, state=tk.DISABLED)
        self.log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Exit button
        bottom = tk.Frame(self.root)
        bottom.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(bottom, text="Exit", command=self.on_exit).pack(side=tk.RIGHT)

    def log_line(self, text):
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, text + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def send_obj(self, obj):
        if not self.connected or not self.sock:
            self.log_line("[CLIENT] Not connected.")
            return
        data = (json.dumps(obj) + "\n").encode("utf-8")
        with self.send_lock:
            try:
                self.sock.sendall(data)
            except Exception as e:
                self.log_line(f"[CLIENT] Send error: {e}")

    def connect(self):
        if self.connected:
            messagebox.showinfo("Info", "Already connected.")
            return
        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        username = self.user_entry.get().strip()
        if not host or not port_str or not username:
            messagebox.showerror("Error", "Host, port, and username are required.")
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer.")
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            f = s.makefile("r")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot connect: {e}")
            return
        self.sock = s
        self.sock_file = f
        self.connected = True
        self.log_line(f"[CLIENT] Connected to {host}:{port}")
        # start receiver thread
        threading.Thread(target=self.receiver_loop, daemon=True).start()
        # send username
        self.send_obj({"action": "set_username", "username": username})
        self.groups_btn.config(state=tk.NORMAL)
        self.join_btn.config(state=tk.NORMAL)
        self.users_btn.config(state=tk.NORMAL)
        self.leave_btn.config(state=tk.NORMAL)
        self.post_btn.config(state=tk.NORMAL)
        self.getmsg_btn.config(state=tk.NORMAL)

    def receiver_loop(self):
        try:
            for line in self.sock_file:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    self.log_line("[CLIENT] Invalid JSON from server")
                    continue
                self.handle_server_message(obj)
        except Exception as e:
            self.log_line(f"[CLIENT] Connection error: {e}")
        finally:
            self.connected = False
            self.log_line("[CLIENT] Disconnected from server.")

    def handle_server_message(self, obj):
        t = obj.get("type")
        if t == "info":
            self.log_line("[INFO] " + obj.get("message", ""))
        elif t == "error":
            self.log_line("[ERROR] " + obj.get("message", ""))
        elif t == "event":
            ev = obj.get("event")
            if ev == "user_joined":
                self.log_line(f"[EVENT] {obj.get('user')} joined {obj.get('group')}")
            elif ev == "user_left":
                self.log_line(f"[EVENT] {obj.get('user')} left {obj.get('group')}")
            elif ev == "new_message":
                self.log_line(
                    f"[NEW MESSAGE] ({obj.get('group')}) "
                    f"ID={obj.get('id')} From={obj.get('sender')} "
                    f"Date={obj.get('date')} Subject={obj.get('subject')}"
                )
            else:
                self.log_line(f"[EVENT] {obj}")
        elif t == "response":
            cmd = obj.get("command")
            if cmd == "groups":
                self.log_line("[GROUPS] " + ", ".join(obj.get("groups", [])))
            elif cmd == "users":
                self.log_line(f"[USERS in {obj.get('group')}] " +
                              ", ".join(obj.get("users", [])))
            elif cmd == "message":
                m = obj.get("message", {})
                self.log_line(f"[MESSAGE {m.get('id')} in {obj.get('group')}]")
                self.log_line(f" From: {m.get('sender')}")
                self.log_line(f" Date: {m.get('timestamp')}")
                self.log_line(f" Subject: {m.get('subject')}")
                self.log_line(" Body:")
                self.log_line(m.get("body", ""))
            else:
                self.log_line(f"[RESPONSE] {obj}")
        elif t == "history":
            group = obj.get("group")
            msgs = obj.get("messages", [])
            self.log_line(f"[HISTORY for {group}] (last {len(msgs)} messages)")
            for m in msgs:
                self.log_line(f"  ID={m.get('id')} From={m.get('sender')} "
                              f"Date={m.get('timestamp')} Subject={m.get('subject')}")
        else:
            self.log_line(f"[SERVER] {obj}")

    def get_groups(self):
        if not self.connected:
            return
        self.send_obj({"action": "groups"})

    def join_group(self):
        if not self.connected:
            return
        g = self.group_entry.get().strip()
        if not g:
            g = "public"
        self.send_obj({"action": "join", "group": g})

    def group_users(self):
        if not self.connected:
            return
        g = self.group_entry.get().strip()
        if not g:
            g = "public"
        self.send_obj({"action": "users", "group": g})

    def leave_group(self):
        if not self.connected:
            return
        g = self.group_entry.get().strip()
        if not g:
            g = "public"
        self.send_obj({"action": "leave", "group": g})

    def post_message(self):
        if not self.connected:
            return
        g = self.group_entry.get().strip()
        if not g:
            g = "public"
        subj = self.subject_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).strip()
        if not subj or not body:
            messagebox.showerror("Error", "Subject and body are required.")
            return
        self.send_obj({"action": "post", "group": g, "subject": subj, "body": body})
        self.body_text.delete("1.0", tk.END)

    def get_message(self):
        if not self.connected:
            return
        g = self.group_entry.get().strip()
        if not g:
            g = "public"
        mid = self.msgid_entry.get().strip()
        if not mid:
            messagebox.showerror("Error", "Message ID required.")
            return
        try:
            mid_int = int(mid)
        except ValueError:
            messagebox.showerror("Error", "Message ID must be integer.")
            return
        self.send_obj({"action": "get_message", "group": g, "id": mid_int})

    def on_exit(self):
        if self.connected and self.sock:
            try:
                self.send_obj({"action": "exit"})
            except Exception:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GuiClient(root)
    root.mainloop()

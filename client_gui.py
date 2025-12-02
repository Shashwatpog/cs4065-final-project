import tkinter as tk
from tkinter import scrolledtext, messagebox
from tkinter import ttk
import socket
import json
import threading

TEAL = "#0A66C2"
TEAL_DARK = "#00695C"
WHITE = "#FFFFFF"
BLACK = "#000000"

class GuiClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Bulletin Board Client (GUI)")
        self.root.configure(bg=WHITE)
        self.sock = None
        self.sock_file = None
        self.connected = False
        self.send_lock = threading.Lock()

        self.font_normal = ("Segoe UI", 10)
        self.font_bold = ("Segoe UI", 10, "bold")
        self.font_header = ("Segoe UI", 14, "bold")

        # default group list; will be updated from server "groups" response
        self.group_list = ["public", "group1", "group2", "group3", "group4", "group5"]

        self.build_ui()

    # Styling helpers

    def style_button(self, button):
        button.configure(
            bg=TEAL,
            fg=WHITE,
            activebackground=TEAL_DARK,
            activeforeground=WHITE,
            relief="flat",
            bd=0,
            font=self.font_bold,
            padx=10,
            pady=5,
            cursor="hand2"
        )

    def style_entry(self, entry):
        entry.configure(
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=TEAL,
            highlightcolor=TEAL,
            font=self.font_normal,
            insertbackground=BLACK,
            bg=WHITE,
            fg=BLACK
        )

    def create_card(self, parent):
        frame = tk.Frame(parent, bg=WHITE, relief="solid", bd=1)
        frame.pack(fill=tk.X, padx=12, pady=10)
        return frame

    def build_ui(self):
        header = tk.Frame(self.root, bg=TEAL, pady=12)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="Bulletin Board Client",
            font=self.font_header,
            bg=TEAL,
            fg=WHITE
        ).pack()

        top = self.create_card(self.root)

        labels = ["Host:", "Port:", "Username:"]
        for i, text in enumerate(labels):
            tk.Label(top, text=text, bg=WHITE, fg=BLACK, font=self.font_bold)\
                .grid(row=0, column=i*2, sticky="w", padx=6)

        self.host_entry = tk.Entry(top, width=15)
        self.host_entry.insert(0, "127.0.0.1")
        self.style_entry(self.host_entry)
        self.host_entry.grid(row=0, column=1, padx=6)

        self.port_entry = tk.Entry(top, width=8)
        self.port_entry.insert(0, "12345")
        self.style_entry(self.port_entry)
        self.port_entry.grid(row=0, column=3, padx=6)

        self.user_entry = tk.Entry(top, width=15)
        self.style_entry(self.user_entry)
        self.user_entry.grid(row=0, column=5, padx=6)

        self.connect_btn = tk.Button(top, text="Connect", command=self.connect)
        self.style_button(self.connect_btn)
        self.connect_btn.grid(row=0, column=6, padx=10)

        self.groups_btn = tk.Button(top, text="Get Groups",
                                    command=self.get_groups, state=tk.DISABLED)
        self.style_button(self.groups_btn)
        self.groups_btn.grid(row=0, column=7, padx=10)

        # Group and message controls
        mid = self.create_card(self.root)

        tk.Label(mid, text="Group:", bg=WHITE, fg=BLACK, font=self.font_bold)\
            .grid(row=0, column=0, sticky="w", padx=5)

        # DROPDOWN instead of entry
        self.group_var = tk.StringVar(value="public")
        self.group_combo = ttk.Combobox(
            mid,
            textvariable=self.group_var,
            values=self.group_list,
            state="readonly",
            width=12
        )
        self.group_combo.grid(row=0, column=1, padx=5)

        self.join_btn = tk.Button(mid, text="Join Group",
                                  command=self.join_group, state=tk.DISABLED)
        self.style_button(self.join_btn)
        self.join_btn.grid(row=0, column=2, padx=5)

        self.users_btn = tk.Button(mid, text="Group Users",
                                   command=self.group_users, state=tk.DISABLED)
        self.style_button(self.users_btn)
        self.users_btn.grid(row=0, column=3, padx=5)

        self.leave_btn = tk.Button(mid, text="Leave Group",
                                   command=self.leave_group, state=tk.DISABLED)
        self.style_button(self.leave_btn)
        self.leave_btn.grid(row=0, column=4, padx=5)

        # Subject + Body
        msg_frame = self.create_card(self.root)
        tk.Label(msg_frame, text="Subject:", bg=WHITE, fg=BLACK,
                 font=self.font_bold).grid(row=0, column=0, sticky="w", padx=5)

        self.subject_entry = tk.Entry(msg_frame, width=40)
        self.style_entry(self.subject_entry)
        self.subject_entry.grid(row=0, column=1, columnspan=3,
                                sticky="we", pady=5, padx=5)

        tk.Label(msg_frame, text="Body:", bg=WHITE, fg=BLACK,
                 font=self.font_bold).grid(row=1, column=0, sticky="nw", padx=5)

        self.body_text = tk.Text(msg_frame, height=4, width=50,
                                 relief="solid", bd=1,
                                 font=self.font_normal,
                                 bg=WHITE, fg=BLACK, insertbackground=BLACK)
        self.body_text.grid(row=1, column=1, columnspan=3,
                            sticky="we", padx=5, pady=5)

        self.post_btn = tk.Button(msg_frame, text="Post",
                                  command=self.post_message, state=tk.DISABLED)
        self.style_button(self.post_btn)
        self.post_btn.grid(row=1, column=4, padx=10, sticky="n")

        # Message retrieval
        tk.Label(msg_frame, text="Msg ID:", bg=WHITE, fg=BLACK,
                 font=self.font_bold).grid(row=2, column=0, sticky="w", padx=5)

        self.msgid_entry = tk.Entry(msg_frame, width=8)
        self.style_entry(self.msgid_entry)
        self.msgid_entry.grid(row=2, column=1, sticky="w", padx=5)

        self.getmsg_btn = tk.Button(msg_frame, text="Get Message",
                                    command=self.get_message, state=tk.DISABLED)
        self.style_button(self.getmsg_btn)
        self.getmsg_btn.grid(row=2, column=2, padx=10, sticky="w")

        # Log area
        log_frame = self.create_card(self.root)
        self.log = scrolledtext.ScrolledText(
            log_frame,
            height=16,
            width=90,
            state=tk.DISABLED,
            bg=WHITE,
            fg=BLACK,
            insertbackground=BLACK,
            font=("Consolas", 10),
            relief="solid",
            bd=1
        )
        self.log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Exit Button
        bottom = tk.Frame(self.root, bg=WHITE)
        bottom.pack(fill=tk.X, padx=12, pady=10)

        exit_btn = tk.Button(bottom, text="Exit", command=self.on_exit)
        self.style_button(exit_btn)
        exit_btn.pack(side=tk.RIGHT)

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

        # Start receiver thread
        threading.Thread(target=self.receiver_loop, daemon=True).start()
        
        # Send username
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
                groups = obj.get("groups", [])
                self.group_list = groups or self.group_list
                self.group_combo["values"] = self.group_list
                # keep current if valid, else default to public / first
                current = self.group_var.get()
                if current not in self.group_list:
                    if "public" in self.group_list:
                        self.group_var.set("public")
                    elif self.group_list:
                        self.group_var.set(self.group_list[0])

                self.log_line("[GROUPS] " + ", ".join(self.group_list))
            elif cmd == "users":
                self.log_line(f"[USERS in {obj.get('group')}] " +
                              ", ".join(obj.get("users", [])))
            elif cmd == "message":
                m = obj.get("message", {})
                self.log_line(f"[MESSAGE {m.get('id')} in {m.get('group')}]")
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

    def _current_group(self):
        g = self.group_var.get().strip()
        if not g:
            g = "public"
        return g

    def join_group(self):
        if not self.connected:
            return
        g = self._current_group()
        self.send_obj({"action": "join", "group": g})

    def group_users(self):
        if not self.connected:
            return
        g = self._current_group()
        self.send_obj({"action": "users", "group": g})

    def leave_group(self):
        if not self.connected:
            return
        g = self._current_group()
        self.send_obj({"action": "leave", "group": g})

    def post_message(self):
        if not self.connected:
            return
        g = self._current_group()
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
        g = self._current_group()
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
    root.option_add("*disabledForeground", "white")
    app = GuiClient(root)
    root.mainloop()

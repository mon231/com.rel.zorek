"""PC app. `python desktop/app.py [shares.json]` opens the window; `--nogui` runs headless and prints status changes.

Needs: pip install -r backend/requirements.txt  (tkinter ships with Python)
"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from zorek_backend import Zorek, new_url, read_config  # noqa: E402

DEFAULT_CONFIG = "shares.json"


def run_headless(z):
    last = None
    while True:
        st = z.status()
        if st != last:
            print(st, flush=True)
            last = st
        time.sleep(1)


def run_gui(z):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    try:  # crisp text on high-DPI Windows
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    root.title("Zorek")
    root.geometry("760x520")
    pad = {"padx": 8, "pady": 4}

    # --- tunnels -------------------------------------------------------------------------------------------------
    top = ttk.LabelFrame(root, text="Tunnels (config is re-read every 2s)")
    top.pack(fill="both", expand=True, **pad)
    cfg_var = tk.StringVar(value=os.path.abspath(z.path))
    row = ttk.Frame(top)
    row.pack(fill="x")
    ttk.Label(row, text="Config").pack(side="left", **pad)
    ttk.Entry(row, textvariable=cfg_var, state="readonly").pack(side="left", fill="x", expand=True)

    def pick_config():
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json")]) or filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            z.path = p
            cfg_var.set(os.path.abspath(p))

    ttk.Button(row, text="Change...", command=pick_config).pack(side="left", **pad)
    tree = ttk.Treeview(top, columns=("url", "target", "state"), show="headings", height=8)
    for c, w in (("url", 330), ("target", 200), ("state", 160)):
        tree.heading(c, text=c.capitalize())
        tree.column(c, width=w)
    tree.pack(fill="both", expand=True, **pad)
    err_var = tk.StringVar()
    ttk.Label(top, textvariable=err_var, foreground="#b00020").pack(fill="x", **pad)

    def copy_selected(_=None):
        sel = tree.selection()
        if sel:
            root.clipboard_clear()
            root.clipboard_append(tree.item(sel[0])["values"][0])

    tree.bind("<Double-1>", copy_selected)
    ttk.Button(top, text="Copy selected URL (or double-click)", command=copy_selected).pack(anchor="e", **pad)

    # --- new URL -------------------------------------------------------------------------------------------------
    new = ttk.LabelFrame(root, text="New public URL (needs your zrok enable token)")
    new.pack(fill="x", **pad)
    token_var, ip_var, port_var, scheme_var, name_var = (tk.StringVar() for _ in range(5))
    ip_var.set("127.0.0.1")
    port_var.set("8000")
    scheme_var.set("http")
    try:
        token_var.set(read_config(z.path).get("enable_token", ""))
    except Exception:
        pass
    fields = [("Enable token", token_var, {"show": "*", "width": 34}), ("Target IP", ip_var, {"width": 16}),
              ("Port", port_var, {"width": 7}), ("Name (optional)", name_var, {"width": 18})]
    for i, (label, var, kw) in enumerate(fields):
        ttk.Label(new, text=label).grid(row=i // 2, column=(i % 2) * 2, sticky="e", **pad)
        ttk.Entry(new, textvariable=var, **kw).grid(row=i // 2, column=(i % 2) * 2 + 1, sticky="w", **pad)
    ttk.Label(new, text="Scheme").grid(row=2, column=0, sticky="e", **pad)
    ttk.Combobox(new, textvariable=scheme_var, values=("http", "https"), width=7, state="readonly").grid(row=2, column=1, sticky="w", **pad)
    msg_var = tk.StringVar()
    create_btn = ttk.Button(new, text="Create URL")
    create_btn.grid(row=2, column=2, sticky="e", **pad)
    ttk.Label(new, textvariable=msg_var).grid(row=3, column=0, columnspan=4, sticky="w", **pad)

    def create():
        create_btn.state(["disabled"])
        msg_var.set("creating...")

        def work():
            try:
                e = new_url(z.path, token_var.get().strip() or None, ip_var.get().strip(), int(port_var.get()),
                            scheme_var.get(), name_var.get().strip() or None)
                root.after(0, lambda: (msg_var.set(f"created {e['public_url']} (copied)"), root.clipboard_clear(),
                                       root.clipboard_append(e["public_url"])))
            except Exception as ex:
                root.after(0, lambda: msg_var.set(f"failed: {ex}"))
            finally:
                root.after(0, lambda: create_btn.state(["!disabled"]))

        threading.Thread(target=work, daemon=True).start()

    create_btn.configure(command=create)

    # --- folder watch --------------------------------------------------------------------------------------------
    watch = ttk.LabelFrame(root, text="Import shares_*.json files from a folder")
    watch.pack(fill="x", **pad)
    watch_var = tk.BooleanVar(value=bool(z.import_dir))
    dir_var = tk.StringVar(value=z.import_dir or os.path.join(os.path.expanduser("~"), "Downloads"))

    def apply_watch():
        z.set_import_dir(dir_var.get() if watch_var.get() else None)

    ttk.Checkbutton(watch, text="Watch", variable=watch_var, command=apply_watch).pack(side="left", **pad)
    ttk.Entry(watch, textvariable=dir_var).pack(side="left", fill="x", expand=True)

    def pick_dir():
        d = filedialog.askdirectory()
        if d:
            dir_var.set(d)
            apply_watch()

    ttk.Button(watch, text="Browse...", command=pick_dir).pack(side="left", **pad)

    # --- refresh -------------------------------------------------------------------------------------------------
    def refresh():
        st = z.status()
        err_var.set(st["error"] or "")
        tree.delete(*tree.get_children())
        for t in st["tunnels"].values():
            tree.insert("", "end", values=(t["url"], t["target"], t["state"]))
        root.after(1000, refresh)

    refresh()
    root.mainloop()


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    z = Zorek(args[0] if args else DEFAULT_CONFIG)
    threading.Thread(target=z.run_forever, daemon=True).start()
    try:
        (run_headless if "--nogui" in argv else run_gui)(z)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main(sys.argv[1:])

"""Keeps every zrok tunnel listed in a shares.json-style config running, and re-syncs when the file changes.

Config: either a list of entries, or {"enable_token": "...", "shares": [entries]} (token needed only on first run;
falls back to env ZROK2_ENABLE_TOKEN). Entry: {"public_token", "tunnel_ip", "tunnel_port", "tunnel_scheme"?, ...}.
"""
import json
import os
import socket
import ssl
import threading
import time

RETRY_SECONDS = 10


def read_config(path):
    with open(path) as f:
        data = json.load(f)
    token, entries = (data.get("enable_token"), data["shares"]) if isinstance(data, dict) else (None, data)
    for e in entries:
        e["public_token"], e["tunnel_ip"], e["tunnel_port"]  # KeyError on a malformed entry
    return token, entries


def _pump(src, dst):
    try:
        data = src.recv(65536)
        while data:
            dst.sendall(data)
            data = src.recv(65536)
    except OSError:
        pass
    finally:
        src.close()
        dst.close()


def _load_ziti(token):
    """Enable the zrok environment once (from the account token), then return a ziti context."""
    import openziti
    from zrok2.environment import root as zroot
    from zrok2.environment.enable import enable

    try:
        root = zroot.Load()
    except FileNotFoundError:  # SDK quirk: metadata.json without environment.json
        root = zroot.Default()
    if not root.IsEnabled():
        enable(root, token or os.environ["ZROK2_ENABLE_TOKEN"], description="zorek")
        with open(zroot.metadataFile(), "w") as f:  # SDK enable() omits it; Load() needs it
            json.dump({"v": zroot.V}, f)
        root = zroot.Load()
    ztx, err = openziti.load(root.ZitiIdentityNamed(root.EnvironmentIdentityName()))
    if err:
        raise RuntimeError(err)
    return ztx


class Tunnel:
    """One public share token -> ip:port. Runs in a daemon thread until stop()."""

    def __init__(self, ztx, entry):
        self.entry = entry
        self.spec = (entry["tunnel_ip"], int(entry["tunnel_port"]), entry.get("tunnel_scheme", "http"))
        self.error = None
        self.stopped = False
        self.srv = None
        self._ztx = ztx
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    @property
    def alive(self):
        return self.thread.is_alive()

    def stop(self):
        self.stopped = True
        if self.srv:
            try:
                self.srv.close()
            except OSError:
                pass

    def _run(self):
        ip, port, scheme = self.spec
        tls = ssl.create_default_context()
        tls.check_hostname, tls.verify_mode = False, ssl.CERT_NONE  # LAN devices are usually self-signed
        try:
            self.srv = self._ztx.bind(self.entry["public_token"])
            self.srv.listen()
            while not self.stopped:
                conn, _ = self.srv.accept()
                try:
                    local = socket.create_connection((ip, port), timeout=10)
                    if scheme == "https":
                        local = tls.wrap_socket(local, server_hostname=ip)
                    local.settimeout(None)
                except OSError as e:
                    self.error = f"cannot reach {ip}:{port}: {e}"
                    conn.close()
                    continue
                threading.Thread(target=_pump, args=(conn, local), daemon=True).start()
                threading.Thread(target=_pump, args=(local, conn), daemon=True).start()
        except Exception as e:
            if not self.stopped:
                self.error = repr(e)


class Zorek:
    def __init__(self, config_path, ztx=None):
        self.path = config_path
        self._ztx = ztx  # injectable for tests
        self.tunnels = {}  # public_token -> Tunnel
        self._started = {}  # public_token -> time of last start attempt
        self.error = None

    def sync(self):
        """Make the running tunnels match the config file (start new, restart changed/dead, stop removed)."""
        try:
            token, entries = read_config(self.path)
            if self._ztx is None:
                self._ztx = _load_ziti(token)
            self.error = None
        except Exception as e:
            self.error = repr(e)
            return
        want = {e["public_token"]: e for e in entries}
        for t in set(self.tunnels) - set(want):
            self.tunnels.pop(t).stop()
        for t, e in want.items():
            cur = self.tunnels.get(t)
            spec = (e["tunnel_ip"], int(e["tunnel_port"]), e.get("tunnel_scheme", "http"))
            if cur and cur.alive and cur.spec == spec:
                continue
            if cur and cur.alive:
                cur.stop()
            elif cur and time.time() - self._started[t] < RETRY_SECONDS:
                continue  # died recently: back off
            self._started[t] = time.time()
            self.tunnels[t] = Tunnel(self._ztx, e)

    def status(self):
        s = {t: ("running" if x.alive and not x.error else x.error or "stopped") for t, x in self.tunnels.items()}
        return {"error": self.error, "tunnels": s}

    def run_forever(self, interval=2):
        while True:  # re-reading the small config every tick is the "watch"; it also restarts dead tunnels
            self.sync()
            time.sleep(interval)

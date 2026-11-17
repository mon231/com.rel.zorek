"""Keeps every zrok tunnel listed in a shares.json-style config running, and re-syncs when the file changes.

Config: either a list of entries, or {"identity": {...}, "enable_token": "...", "shares": [entries]}.
Shares can only be bound by the zrok environment that created them, so on a device without ~/.zrok2 put that PC's
~/.zrok2/identities/environment.json content in "identity". Without it, "enable_token" (or env ZROK2_ENABLE_TOKEN)
creates a fresh environment (fine only for shares created by that new environment). Entry: {"public_token", "tunnel_ip", "tunnel_port", "tunnel_scheme"?, ...}.
"""
import json
import os
import socket
import sys
import ssl
import threading
import time
import urllib.request

RETRY_SECONDS = 10


def read_config(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        data = {"shares": data}
    for e in data["shares"]:
        e["public_token"], e["tunnel_ip"], e["tunnel_port"]  # KeyError on a malformed entry
    return data


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


def _enable(token, home):
    """zrok `enable` over plain HTTPS (zrok2's SDK needs pydantic-core, which has no Android build)."""
    api = os.environ.get("ZROK2_API_ENDPOINT", "https://api-v2.zrok.io").rstrip("/")
    req = urllib.request.Request(
        api + "/api/v2/enable",
        data=json.dumps({"host": socket.gethostname(), "description": "zorek"}).encode(),
        headers={"x-token": token, "Content-Type": "application/zrok.v1+json", "Accept": "application/json, application/zrok.v1+json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)
    os.makedirs(os.path.join(home, "identities"), exist_ok=True)
    with open(os.path.join(home, "identities", "environment.json"), "w") as f:
        f.write(res["cfg"])
    with open(os.path.join(home, "environment.json"), "w") as f:  # same layout as the zrok2 SDK/CLI
        json.dump({"zrok_token": token, "ziti_identity": res["identity"], "api_endpoint": api}, f)


def _load_ziti(cfg):
    """Return a ziti context from the identity in the config, else the saved one, else a freshly enabled one."""
    import openziti

    home = os.path.join(os.path.expanduser("~"), ".zrok2")
    ident = os.path.join(home, "identities", "environment.json")
    if cfg.get("identity"):
        os.makedirs(os.path.dirname(ident), exist_ok=True)
        with open(ident, "w") as f:
            json.dump(cfg["identity"], f)
    elif not os.path.isfile(ident):
        _enable(cfg.get("enable_token") or os.environ["ZROK2_ENABLE_TOKEN"], home)
    ztx, err = openziti.load(ident)
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
            self._log("listening")
            while not self.stopped:
                try:
                    conn, _ = self.srv.accept()
                except BlockingIOError:  # on Android libziti's listener is non-blocking (blocks on Windows/Linux)
                    time.sleep(0.05)
                    continue
                conn.setblocking(True)
                self._log("connection")
                try:
                    local = socket.create_connection((ip, port), timeout=10)
                    if scheme == "https":
                        local = tls.wrap_socket(local, server_hostname=ip)
                    local.settimeout(None)
                except OSError as e:
                    self._fail(f"cannot reach {ip}:{port}: {e}")
                    conn.close()
                    continue
                threading.Thread(target=_pump, args=(conn, local), daemon=True).start()
                threading.Thread(target=_pump, args=(local, conn), daemon=True).start()
        except Exception as e:
            if not self.stopped:
                self._fail(repr(e))

    def _log(self, msg):
        print(f"tunnel {self.entry['public_token']}: {msg}", file=sys.stderr, flush=True)

    def _fail(self, msg):
        self.error = msg
        self._log(msg)


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
            cfg = read_config(self.path)
            entries = cfg["shares"]
            if self._ztx is None:
                self._ztx = _load_ziti(cfg)
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

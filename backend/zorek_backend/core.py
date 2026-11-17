"""Keeps every zrok tunnel listed in a shares.json-style config running, and re-syncs when the file changes.

Config: a list of entries, or {"shares": [entries], "identity": {...}, "env_zid": "...", "enable_token": "..."}.
Entry: {"public_token", "tunnel_ip", "tunnel_port", "tunnel_scheme"?, "public_url"?, "identity"?, "env_zid"?}.
A share can only be bound by the zrok environment that created it, so an entry's ziti `identity` is that
environment's (entry value, else the top-level one, else ~/.zrok2/identities/environment.json of the zrok CLI).
"""
import glob
import hashlib
import json
import os
import socket
import ssl
import sys
import threading
import time
import uuid

from . import zrokapi

RETRY_SECONDS = 10


def _zrok_home():
    return os.path.join(os.path.expanduser("~"), ".zrok2")


def _normalize(data):
    cfg = {"shares": data} if isinstance(data, list) else data
    for e in cfg["shares"]:
        e["public_token"], e["tunnel_ip"], e["tunnel_port"]  # KeyError on a malformed entry
    return cfg


def read_config(path):
    with open(path) as f:
        return _normalize(json.load(f))


def write_config(path, cfg):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="\n") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, path)  # atomic: the watcher never sees half a file


def new_url(path, enable_token, ip, port, scheme="http", name=None):
    """Create a new public URL forwarding to ip:port and append it to the config. Returns the new entry.

    The account enable token is remembered in the config. An existing environment (identity+env_zid on any entry or
    at top level) is reused; otherwise a new one is enabled.
    """
    cfg = read_config(path) if os.path.exists(path) else {"shares": []}
    token = enable_token or cfg.get("enable_token") or os.environ.get("ZROK2_ENABLE_TOKEN")
    if not token:
        raise ValueError("enable token required")
    env = next(({"identity": c["identity"], "env_zid": c["env_zid"]} for c in [cfg, *cfg["shares"]]
                if c.get("identity") and c.get("env_zid")), None) or zrokapi.enable(token)
    share_token, url = zrokapi.create_share(token, env["env_zid"], name or "zorek" + uuid.uuid4().hex[:8])
    entry = {"public_token": share_token, "public_url": url, "tunnel_ip": ip, "tunnel_port": int(port),
             "tunnel_scheme": scheme, **env}
    cfg["enable_token"] = token
    cfg["shares"].append(entry)
    write_config(path, cfg)
    return entry


def import_new_files(config_path, directory):
    """Merge every not-yet-seen shares_*.json from `directory` into the config. Returns (files merged, errors).

    An unreadable file (e.g. still downloading) is skipped and retried on the next call, without blocking the others.
    """
    seen_path = config_path + ".imported"
    try:
        with open(seen_path) as f:
            seen = set(json.load(f))
    except (OSError, ValueError):
        seen = set()
    merged, errors = [], []
    for f in sorted(glob.glob(os.path.join(directory, "shares_*.json"))):
        st = os.stat(f)
        key = f"{os.path.basename(f)}:{st.st_mtime_ns}:{st.st_size}"
        if key in seen:
            continue
        try:
            with open(f) as fh:
                data = _normalize(json.load(fh))
        except (OSError, ValueError, KeyError, TypeError) as e:
            errors.append(f"{os.path.basename(f)}: {e!r}")
            continue
        cfg = read_config(config_path) if os.path.exists(config_path) else {"shares": []}
        index = {e["public_token"]: i for i, e in enumerate(cfg["shares"])}
        for e in data["shares"]:
            for k in ("identity", "env_zid"):  # keep the entry self-contained: the file's defaults travel with it
                if k not in e and data.get(k):
                    e[k] = data[k]
            if e["public_token"] in index:
                cfg["shares"][index[e["public_token"]]] = e
            else:
                cfg["shares"].append(e)
        write_config(config_path, cfg)
        seen.add(key)
        with open(seen_path, "w") as fh:
            json.dump(sorted(seen), fh)
        merged.append(f)
    return merged, errors


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


def _spec(entry):
    return (entry["tunnel_ip"], int(entry["tunnel_port"]), entry.get("tunnel_scheme", "http"))


class Tunnel:
    """One public share token -> ip:port. Runs in a daemon thread until stop()."""

    def __init__(self, ztx, entry):
        self.entry = entry
        self.spec = _spec(entry)
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

    def _log(self, msg):
        print(f"tunnel {self.entry['public_token']}: {msg}", file=sys.stderr, flush=True)

    def _fail(self, msg):
        self.error = msg
        self._log(msg)

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


class Zorek:
    def __init__(self, config_path, ztx=None, import_dir=None):
        self.path = config_path
        self.import_dir = import_dir
        self._injected = ztx  # tests inject a fake ziti context
        self._ctx = {}  # identity file path -> ziti context
        self.tunnels = {}  # public_token -> Tunnel
        self._started = {}  # public_token -> time of last start attempt
        self.error = None

    def set_import_dir(self, directory):
        self.import_dir = directory or None

    def _ztx_for(self, entry, cfg):
        if self._injected:
            return self._injected
        import openziti

        ident = entry.get("identity") or cfg.get("identity")
        if ident:
            blob = json.dumps(ident, sort_keys=True)
            path = os.path.join(_zrok_home(), "identities", "zorek-" + hashlib.sha1(blob.encode()).hexdigest()[:12] + ".json")
            if not os.path.isfile(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(blob)
        else:
            path = os.path.join(_zrok_home(), "identities", "environment.json")  # the zrok CLI/SDK environment
        if path not in self._ctx:
            ztx, err = openziti.load(path)
            if err:
                raise RuntimeError(err)
            self._ctx[path] = ztx
        return self._ctx[path]

    def sync(self):
        """Make the running tunnels match the config file (start new, restart changed/dead, stop removed)."""
        try:
            _, bad = import_new_files(self.path, self.import_dir) if self.import_dir else (None, [])
            cfg = read_config(self.path)
            self.error = "; ".join(bad) or None
        except Exception as e:
            self.error = repr(e)
            return
        want = {e["public_token"]: e for e in cfg["shares"]}
        for t in set(self.tunnels) - set(want):
            self.tunnels.pop(t).stop()
        for t, e in want.items():
            cur = self.tunnels.get(t)
            if cur and cur.alive and cur.spec == _spec(e) and cur.entry.get("identity") == e.get("identity"):
                continue
            if cur and cur.alive:
                cur.stop()
            elif cur and time.time() - self._started[t] < RETRY_SECONDS:
                continue  # died recently: back off
            self._started[t] = time.time()
            try:
                self.tunnels[t] = Tunnel(self._ztx_for(e, cfg), e)
            except Exception as ex:  # e.g. missing identity file
                self.error = f"{t}: {ex!r}"

    def status(self):
        s = {t: {"url": x.entry.get("public_url", t), "target": "{2}://{0}:{1}".format(*x.spec),
                 "state": "running" if x.alive and not x.error else x.error or "stopped"}
             for t, x in self.tunnels.items()}
        return {"error": self.error, "tunnels": s}

    def run_forever(self, interval=2):
        while True:  # re-reading the small config every tick is the "watch"; it also restarts dead tunnels
            self.sync()
            time.sleep(interval)

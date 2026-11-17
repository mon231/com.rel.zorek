import json as _json
import os as _os
import threading as _threading

from .core import Zorek, import_new_files, new_url, read_config, write_config  # noqa: F401

_z = None


def start(config_path, home, import_dir=None):
    """Android entry (called from the foreground service): run Zorek on config_path in a background thread."""
    global _z
    if _z is None:
        _os.environ["HOME"] = home  # ~/.zrok2 lives in the app's private dir
        _z = Zorek(config_path, import_dir=import_dir)
        _threading.Thread(target=_z.run_forever, daemon=True).start()


def stop():
    """Android entry: stop all tunnels; start() can be called again afterwards."""
    global _z
    if _z:
        _z.stop()
        _z = None


def set_import_dir(directory):
    if _z:
        _z.set_import_dir(directory)


def status_json():
    """Machine readable status for the notification: {"error", "tunnels": {token: {url, target, state}}}."""
    return _json.dumps(_z.status() if _z else {"error": None, "tunnels": {}})


def status():
    """Human readable status for the Android UI."""
    if not _z:
        return "not started"
    st = _z.status()
    lines = [f"{t['url']} -> {t['target']}: {t['state']}" for t in st["tunnels"].values()]
    return "\n".join(([f"error: {st['error']}"] if st["error"] else []) + lines) or "no tunnels"


def create_url(config_path, enable_token, ip, port, scheme, name):
    """Android entry: new public URL (blocking, network); returns the URL."""
    return new_url(config_path, enable_token or None, ip, int(port), scheme or "http", name or None)["public_url"]

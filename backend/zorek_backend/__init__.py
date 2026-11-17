from .core import Zorek, read_config  # noqa: F401
import json as _json
import os as _os
import threading as _threading

_z = None


def start(config_path, home):
    """Android entry (called from the foreground service): run Zorek on config_path in a background thread."""
    global _z
    if _z is None:
        _os.environ["HOME"] = home  # ~/.zrok2 lives in the app's private dir
        _z = Zorek(config_path)
        _threading.Thread(target=_z.run_forever, daemon=True).start()


def status():
    return _json.dumps(_z.status(), indent=1) if _z else "not started"

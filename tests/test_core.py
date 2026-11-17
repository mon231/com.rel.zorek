import json
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from zorek_backend import Zorek  # noqa: E402


class FakeSrv:
    def __init__(self):
        self.closed = threading.Event()

    def listen(self):
        pass

    def accept(self):
        self.closed.wait()
        raise OSError("closed")

    def close(self):
        self.closed.set()


class FakeZtx:
    def __init__(self):
        self.bound = []

    def bind(self, token):
        self.bound.append(token)
        return FakeSrv()


def entry(tok, port=1):
    return {"public_token": tok, "tunnel_ip": "127.0.0.1", "tunnel_port": port}


class T(unittest.TestCase):
    def test_sync(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "shares.json")
        ztx = FakeZtx()
        z = Zorek(p, ztx)

        json.dump([entry("a"), entry("b")], open(p, "w"))
        z.sync(); time.sleep(0.2)
        self.assertEqual(sorted(ztx.bound), ["a", "b"])
        self.assertEqual(z.status()["tunnels"], {"a": "running", "b": "running"})

        json.dump({"shares": [entry("a", 2)]}, open(p, "w"))  # a changed, b removed
        z.sync(); time.sleep(0.2)
        self.assertEqual(sorted(z.tunnels), ["a"])
        self.assertEqual(ztx.bound.count("a"), 2)  # restarted with new spec
        self.assertTrue(z.tunnels["a"].alive)

        open(p, "w").write("{bad")  # bad config keeps tunnels running
        z.sync()
        self.assertIsNotNone(z.status()["error"])
        self.assertTrue(z.tunnels["a"].alive)


if __name__ == "__main__":
    unittest.main()

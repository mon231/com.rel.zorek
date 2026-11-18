import json
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from zorek_backend import Zorek, import_new_files, new_url, read_config, zrokapi  # noqa: E402


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


def entry(tok, port=1, **kw):
    return {"public_token": tok, "tunnel_ip": "127.0.0.1", "tunnel_port": port, **kw}


def wait(cond, timeout=10):
    """Poll until cond() is true (threads start at their own pace, slower on CI runners)."""
    end = time.time() + timeout
    while not cond() and time.time() < end:
        time.sleep(0.02)


def dump(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f)


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = os.path.join(self.d, "shares.json")

    def test_blocked_identity_does_not_block_others(self):
        release = threading.Event()
        good = FakeZtx()

        class Z(Zorek):
            def _ztx_for(self, entry, cfg):
                if entry["public_token"] == "stuck":
                    release.wait()  # like openziti.load() with a revoked identity
                return good

        z = Z(self.p)
        dump(self.p, [entry("stuck"), entry("ok")])
        z.sync()
        wait(lambda: z.status()["tunnels"].get("ok", {}).get("state") == "running")
        st = z.status()["tunnels"]
        self.assertEqual((st["stuck"]["state"], st["ok"]["state"]), ("connecting", "running"))
        release.set(); z.stop()

    def test_stop(self):
        ztx = FakeZtx()
        z = Zorek(self.p, ztx)
        dump(self.p, [entry("a")])
        th = threading.Thread(target=z.run_forever, args=(0.05,), daemon=True)
        th.start()
        wait(lambda: z.tunnels.get("a") and z.tunnels["a"].alive)
        z.stop()
        th.join(5)
        self.assertFalse(th.is_alive())
        self.assertEqual(z.tunnels, {})

    def test_sync(self):
        ztx = FakeZtx()
        z = Zorek(self.p, ztx)

        dump(self.p, [entry("a"), entry("b")])
        z.sync(); wait(lambda: all(t["state"] == "running" for t in z.status()["tunnels"].values()) and len(z.tunnels) == 2)
        self.assertEqual(sorted(ztx.bound), ["a", "b"])
        self.assertEqual({t: s["state"] for t, s in z.status()["tunnels"].items()}, {"a": "running", "b": "running"})

        dump(self.p, {"shares": [entry("a", 2)]})  # a changed, b removed
        z.sync(); wait(lambda: ztx.bound.count("a") == 2)
        self.assertEqual(sorted(z.tunnels), ["a"])
        self.assertEqual(ztx.bound.count("a"), 2)  # restarted with new spec
        self.assertTrue(z.tunnels["a"].alive)

        with open(self.p, "w") as f:
            f.write("{bad")  # bad config keeps tunnels running
        z.sync()
        self.assertIsNotNone(z.status()["error"])
        self.assertTrue(z.tunnels["a"].alive)

    def test_new_url_enables_once_and_remembers_token(self):
        calls = []
        zrokapi.enable = lambda t: calls.append(("enable", t)) or {"identity": {"id": "x"}, "env_zid": "Z1"}
        zrokapi.create_share = lambda t, z, n: calls.append(("share", t, z, n)) or ("tok" + str(len(calls)), f"https://{n}.shares.zrok.io")

        e1 = new_url(self.p, "SECRET", "10.0.0.5", "8000", "https", "mine")
        self.assertEqual(e1["public_url"], "https://mine.shares.zrok.io")
        self.assertEqual((e1["tunnel_ip"], e1["tunnel_port"], e1["tunnel_scheme"], e1["env_zid"]), ("10.0.0.5", 8000, "https", "Z1"))

        e2 = new_url(self.p, None, "127.0.0.1", 9000)  # token remembered, environment reused
        self.assertEqual([c[0] for c in calls], ["enable", "share", "share"])
        cfg = read_config(self.p)
        self.assertEqual(cfg["enable_token"], "SECRET")
        self.assertEqual([s["public_token"] for s in cfg["shares"]], [e1["public_token"], e2["public_token"]])
        with self.assertRaises(ValueError):
            os.remove(self.p)
            os.environ.pop("ZROK2_ENABLE_TOKEN", None)
            new_url(self.p, None, "127.0.0.1", 1)

    def test_import_folder(self):
        dl = os.path.join(self.d, "Download")
        os.makedirs(dl)
        dump(self.p, {"shares": [entry("old", 1, identity={"id": "mine"})]})
        dump(os.path.join(dl, "shares_a.json"), {"identity": {"id": "theirs"}, "env_zid": "Z9", "shares": [entry("n1"), entry("old", 5)]})
        dump(os.path.join(dl, "other.json"), [entry("ignored")])
        with open(os.path.join(dl, "shares_half.json"), "w") as f:
            f.write("{")  # still downloading

        merged, errors = import_new_files(self.p, dl)  # the broken file does not block the good one
        self.assertEqual((len(merged), len(errors)), (1, 1))
        os.remove(os.path.join(dl, "shares_half.json"))
        shares = {s["public_token"]: s for s in read_config(self.p)["shares"]}
        self.assertEqual(sorted(shares), ["n1", "old"])
        self.assertEqual(shares["n1"]["identity"], {"id": "theirs"})  # file defaults travel with each entry
        self.assertEqual(shares["old"]["tunnel_port"], 5)  # same token: replaced
        self.assertEqual(import_new_files(self.p, dl), ([], []))  # each file version is imported once

    def test_zorek_imports_when_watching(self):
        dl = os.path.join(self.d, "Download")
        os.makedirs(dl)
        dump(self.p, {"shares": []})
        ztx = FakeZtx()
        z = Zorek(self.p, ztx, import_dir=dl)
        dump(os.path.join(dl, "shares_x.json"), [entry("t1")])
        z.sync(); wait(lambda: ztx.bound == ["t1"])
        self.assertEqual(ztx.bound, ["t1"])
        z.set_import_dir(None)  # feature off: new files are ignored
        dump(os.path.join(dl, "shares_y.json"), [entry("t2")])
        z.sync(); time.sleep(0.3)  # negative check: give a wrongly started tunnel the time to show up
        self.assertEqual(ztx.bound, ["t1"])


if __name__ == "__main__":
    unittest.main()

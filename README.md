# com.rel.zorek

Keeps every [zrok](https://zrok.io) tunnel listed in a `shares.json`-style config running, on **PC (GUI)** and
**Android**. One Python backend (`backend/zorek_backend`) is shared by both; the config is re-read every 2 seconds, so
tunnels are started, changed, stopped and restarted live.

**Documentation: https://mon231.github.io/com.rel.zorek/**

- Create a new public URL from your zrok enable token (GUI button / app form), on the same URL forever.
- Android: foreground service, Downloads watch that imports `shares_*.json` files (feature flag).
- Works for local servers and for any `ip:port` on your LAN, `http` or `https` targets.

## Quick start

```
pip install openziti
python desktop/app.py            # GUI, uses ./shares.json
python desktop/app.py --nogui x.json
python tests/test_core.py        # backend tests
```

Android: install the APK from the [releases](https://github.com/mon231/com.rel.zorek/releases). Build instructions
(libziti via the NDK in Docker, Gradle, CI, releases): see the Development page of the docs.

> `shares.json` and `shares_*.json` contain your zrok token / private key. Never commit or share them.

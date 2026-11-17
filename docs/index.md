# Zorek

Zorek keeps every [zrok](https://zrok.io) tunnel listed in a `shares.json`-style config running.

- One Python backend (`backend/zorek_backend`) shared by the PC app and the Android app.
- The config file is re-read every 2 seconds: tunnels are started, changed or stopped live, and tunnels that died are restarted.
- Each tunnel forwards a public zrok share token to any `ip:port` reachable from the device (`http` or `https` backend).

## PC

```
pip install openziti
python desktop/app.py shares.json
```

## Android

Install the APK from the latest [release](https://github.com/mon231/com.rel.zorek/releases), paste your config in the app and press **Save config**. A foreground service keeps the tunnels alive.

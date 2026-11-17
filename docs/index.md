# Zorek

Zorek keeps your [zrok](https://zrok.io) public URLs alive. You give it a list of *shares* (a public zrok URL and the
`ip:port` it should forward to) and it makes sure **every tunnel is running**, forever: it starts new ones, restarts
the ones that die, and picks up edits to the config file within two seconds.

It runs as a **PC app** (Windows/Linux, with a GUI) and as an **Android app** (`com.rel.zorek`), both on top of the
same Python backend.

## What you can do

| I want to... | Go to |
|--------------|-------|
| Get a zrok account and my enable token, see my shares, know the free limits | [Get a zrok account](getting-started.md) |
| Expose a local web server (`localhost:8000`) on a public https URL | [Creating URLs](creating-urls.md) |
| Expose a device on my LAN (a camera, a NAS, a smart-home hub) through a public URL | [Config reference](config.md) |
| Run it on my phone so the URLs stay up without a PC | [Android app](android.md) |
| Move shares between my PC and my phone | [Importing shares files](importing.md) |
| Understand what is going on under the hood | [Architecture](how-it-works.md) |

## 60-second start (PC)

```
pip install openziti
python desktop/app.py            # opens the window, uses ./shares.json
```

1. In the window, paste your zrok **enable token** (the account token from the zrok web console).
2. Type the target (`127.0.0.1`, port `8000`) and press **Create URL**.
3. The new public URL appears in the table, is copied to your clipboard, and is already being served.

Close the window and the tunnels stop; start it again and they come back, on the **same URLs**.

## 60-second start (Android)

1. Install `zorek-vX.Y.Z.apk` from the [releases page](https://github.com/mon231/com.rel.zorek/releases).
2. Open the app, allow notifications (a foreground service keeps the tunnels alive).
3. Fill *New public URL* (enable token, target IP, port) and press **Create URL**.

!!! tip "Same URL on PC and phone"
    Create the URL on one device, then move the generated `shares_*.json` to the other. See
    [Importing shares files](importing.md).

## Key facts

- A URL is **stable**: it is reserved in your zrok account until *you* delete it. Zorek never deletes shares.
- Zorek only forwards; it does not run a web server. The target (`ip:port`, `http` or `https`) must already be up.
- Everything is described by one JSON file, so it is easy to back up, diff and script.

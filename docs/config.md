# Config reference

Zorek is driven by one JSON file, `shares.json` by default. The file is **re-read every 2 seconds**, so you can edit it
by hand, from the Android editor, from a script, or let the app edit it for you.

## Two accepted shapes

=== "Object (what the apps write)"

    ```json
    {
      "enable_token": "your zrok account token",
      "identity": { "...": "default ziti identity for entries without their own" },
      "env_zid": "default zrok environment id",
      "shares": [
        {
          "public_token": "74er67ijxyd8",
          "public_url": "https://tunneltest12013.shares.zrok.io",
          "tunnel_ip": "127.0.0.1",
          "tunnel_port": 8000
        },
        {
          "public_token": "p9ywvje0ac13",
          "public_url": "https://ariel-smart-home.shares.zrok.io",
          "tunnel_ip": "10.0.0.5",
          "tunnel_port": 18972,
          "tunnel_scheme": "https"
        }
      ]
    }
    ```

=== "Plain list (legacy)"

    ```json
    [
      {"public_token": "74er67ijxyd8", "tunnel_ip": "127.0.0.1", "tunnel_port": 8000}
    ]
    ```

    A plain list is the original `shares.json` format. It works on a PC where the zrok CLI/SDK environment already
    exists in `~/.zrok2` (see [identity resolution](#identity-resolution)).

## Entry keys

| Key | Required | Meaning |
|-----|----------|---------|
| `public_token` | yes | The zrok **share token**. This is what Zorek binds to; it identifies the share, not the URL. |
| `tunnel_ip` | yes | Where to connect when a visitor arrives: IPv4/IPv6 address or hostname reachable **from the device running Zorek**. |
| `tunnel_port` | yes | TCP port on `tunnel_ip`. |
| `tunnel_scheme` | no | `http` (default) or `https`. With `https`, Zorek speaks TLS to the target and **does not verify the certificate** (LAN devices are usually self-signed). |
| `public_url` | no | Informational: shown in the UI. Written by *Create URL*. Not used for routing. |
| `identity` | no | The ziti identity (JSON object) of the zrok environment that **created** this share. See below. |
| `env_zid` | no | The zrok environment id of that environment. Needed only to create more shares in the same environment. |

Unknown keys are kept as they are. A malformed entry (missing a required key) makes the *whole file* invalid: the
error is shown in the app and the **tunnels that are already running keep running** with their last good config.

## Top-level keys (object form)

| Key | Meaning |
|-----|---------|
| `shares` | The list of entries. |
| `enable_token` | Your zrok account token. Remembered by *Create URL* so you only type it once. Optional. |
| `identity`, `env_zid` | Defaults applied to entries that do not carry their own. Optional. |

## Identity resolution

A zrok share can only be bound by the **zrok environment that created it**. Zorek therefore needs, per entry, the
ziti identity of that environment. For each entry it uses the first of:

1. the entry's own `identity`;
2. the top-level `identity`;
3. the identity file of the zrok CLI/SDK on the same machine: `~/.zrok2/identities/environment.json`.

Entries with different identities can live in the same file; Zorek keeps one connection per distinct identity.
Identities embedded in the config are written to `~/.zrok2/identities/zorek-<hash>.json` (on Android that is inside the
app's private storage) before use.

## What changes take effect, and when

| Edit | Effect (within ~2 s) |
|------|----------------------|
| Add an entry | its tunnel starts |
| Remove an entry | its tunnel stops (the zrok share itself is **not** deleted) |
| Change `tunnel_ip`, `tunnel_port`, `tunnel_scheme` or `identity` | the tunnel restarts with the new target |
| Edit anything else | nothing restarts |
| Save invalid JSON | error is shown; running tunnels are untouched |

A tunnel whose thread dies (network drop, bind failure) is restarted automatically, at most once every 10 seconds per
share.

## Where the file is

| Platform | Default |
|----------|---------|
| PC | `./shares.json` in the current directory, or the path you pass: `python desktop/app.py C:\path\shares.json`. The GUI can switch it with **Change...**. |
| Android | `files/shares.json` in the app's private storage, edited from the in-app editor. |

Next to the config, Zorek keeps `shares.json.imported` (the list of already imported files, see
[Importing shares files](importing.md)).

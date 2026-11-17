# Config

```json
{
  "identity": { "...": "contents of ~/.zrok2/identities/environment.json" },
  "enable_token": "optional account token, only used when there is no identity",
  "shares": [
    {"public_token": "74er67ijxyd8", "tunnel_ip": "127.0.0.1", "tunnel_port": 8000},
    {"public_token": "p9ywvje0ac13", "tunnel_ip": "10.0.0.5", "tunnel_port": 18972, "tunnel_scheme": "https"}
  ]
}
```

A plain list of share entries (the old `shares.json`) also works on a PC that already has `~/.zrok2`.

| Key | Meaning |
|-----|---------|
| `public_token` | zrok share token to serve |
| `tunnel_ip`, `tunnel_port` | where connections are forwarded |
| `tunnel_scheme` | `http` (default) or `https`; certificates of `https` backends are not verified |
| `identity` | ziti identity of the zrok environment that **created** the shares |

!!! note
    A share can only be bound by the zrok environment that created it, so a device that has no `~/.zrok2`
    (Android) needs that environment's identity in the config. A freshly enabled environment cannot bind shares
    created elsewhere.

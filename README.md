# com.rel.zorek

Keeps every zrok tunnel listed in a `shares.json`-style config running. Same Python backend (`backend/zorek_backend`) on PC and Android; the config file is re-read every 2s (tunnels added/changed/removed live, dead ones restarted).

## Config
```json
{
  "identity": { "...": "contents of ~/.zrok2/identities/environment.json of the PC that created the shares" },
  "shares": [
    {"public_token": "74er67ijxyd8", "tunnel_ip": "127.0.0.1", "tunnel_port": 8000},
    {"public_token": "p9ywvje0ac13", "tunnel_ip": "10.0.0.5", "tunnel_port": 18972, "tunnel_scheme": "https"}
  ]
}
```
A plain list (old `shares.json`) also works on PC where `~/.zrok2` already exists. Shares can only be bound by the zrok environment that created them, hence `identity` on Android.

## PC
`pip install openziti` then `python desktop/app.py [shares.json]`

## Android
1. `docker build -t zorek-native native && docker run --rm -v zorek-work:/work -v "%cd%/native/out:/out" zorek-native` (libziti 1.18.3 for arm64-v8a / armeabi-v7a / x86_64 via the NDK + vcpkg)
2. `./gradlew assembleDebug` (JDK 17+, e.g. Android Studio's JBR)
3. Install, edit the config in the app, Save.

Tests: `python tests/test_core.py`

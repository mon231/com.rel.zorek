# Development

## Repository layout

```
backend/zorek_backend/   shared Python backend (PC + Android)
  core.py                config, Tunnel, Zorek (sync loop), new_url, import_new_files
  zrokapi.py             tiny zrok v2 HTTP client (enable, create share)
  __init__.py            Android entry points (start, status, create_url, set_import_dir)
desktop/app.py           PC app: tkinter GUI, --nogui for headless
app/                     Android app (Kotlin): MainActivity, TunnelService
vendor/openziti/         openziti-py 1.7.1, patched to load libziti.so by name on Android
native/                  Dockerfile + script that builds libziti.so for the 3 ABIs
tests/test_core.py       backend tests (no network, no zrok account needed)
docs/, mkdocs.yml        this documentation (Material for MkDocs)
.github/workflows/       CI
```

## Run the tests

```
python tests/test_core.py
```

They use a fake ziti context, so they need neither network nor `openziti`.

## Run the PC app from source

```
pip install openziti
python desktop/app.py              # GUI
python desktop/app.py --nogui x.json   # headless, prints status changes
```

## Build the Android app

1. Build `libziti.so` (once; ~20 minutes, cached afterwards):

    ```
    docker build -t zorek-native native
    docker run --rm -v zorek-work:/work -v "$PWD/native/out:/out" zorek-native
    ```

    The image contains the **Linux** NDK r28b and vcpkg. The script builds ziti-sdk-c 1.18.3 (the version openziti-py
    1.7.1 expects) for `arm64-v8a`, `armeabi-v7a`, `x86_64` at API 28, release-only, and strips the result into
    `native/out/<abi>/libziti.so`.

2. Build the app (JDK 17+, Android SDK 35, Python 3.11 on `PATH` for Chaquopy):

    ```
    ./gradlew assembleDebug
    adb install -r app/build/outputs/apk/debug/app-debug.apk
    ```

!!! note "Why libziti is built here"
    `openziti` on PyPI only ships sources that download a *desktop* libziti at install time. There is no Android build
    and Chaquopy has no wheel for it, so the library is compiled from source and bundled as a JNI library.

## Why the backend does not use the zrok2 SDK

The `zrok2` Python SDK depends on `pydantic-core` (Rust), which Chaquopy cannot provide. The backend only needs three
HTTP calls (enable, create name, create share), so `zrokapi.py` makes them directly with `urllib`. The same code runs on
PC and Android.

## CI/CD

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `build.yml` | every push / PR | backend tests, then builds the debug APK (libziti is cached on the hash of `native/`) |
| `desktop.yml` | every push / PR | tests, then a PyInstaller GUI binary on Linux and Windows |
| `release.yml` | tag `v*` pushed or created | builds APK + desktop binaries and creates a **draft** release with them |
| `docs.yml` | a release is **published** | builds this site with `mkdocs build --strict` from the release's tag and deploys it to GitHub Pages |

### Releasing

1. Make sure `main` is green.
2. Create the tag on the commit to release and push it: `git tag v0.1.1 && git push origin v0.1.1` (creating the tag in
   the GitHub UI works too). The **Release** workflow builds everything and creates the **draft** release `v0.1.1`.
   Re-running the workflow for the same tag refreshes the assets of that release.
3. Open the draft release on GitHub, check the assets (APK, `zorek-linux-x64`, `zorek-windows-x64.exe`), edit the notes
   and **publish**. Publishing triggers the **Docs** workflow, which builds and deploys the site from that tag.

Docs are therefore never published from branches or drafts: the site always matches the latest published release. The
`github-pages` environment must allow deployments from tags `v*` (Settings, Environments).

The APK is signed with [`signapp`](https://pypi.org/project/signapp/) using its built-in keystore, so every release is
signed with the same key and updates install in place.

## Backend API (for scripting)

```python
from zorek_backend import Zorek, new_url, import_new_files, read_config

entry = new_url("shares.json", "ENABLE_TOKEN", "127.0.0.1", 8000)   # -> {"public_url": ..., ...}

z = Zorek("shares.json", import_dir="C:/Users/me/Downloads")        # import_dir optional
z.sync()                      # one reconcile pass (run_forever() loops every 2 s)
print(z.status())             # {"error": None, "tunnels": {"<token>": {"url", "target", "state"}}}
```

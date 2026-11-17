# Android app

Package `com.rel.zorek`. The same Python backend as the PC app runs inside the app (through
[Chaquopy](https://chaquo.com/chaquopy/)), next to `libziti.so`, the native zrok/ziti library built with the NDK.

| | |
|---|---|
| minSdk | 28 (Android 9) |
| ABIs | `arm64-v8a`, `armeabi-v7a`, `x86_64` (emulator) |
| Install | sideload the APK from the [releases page](https://github.com/mon231/com.rel.zorek/releases) |

## Screen

The single screen has four parts, top to bottom:

1. **Tunnels**: one line per share, `public-url -> target: state`. State is `running` or the last error. Refreshed
   every 2 seconds.
2. **New public URL**: enable token, target IP, target port, optional public name, *target speaks https* checkbox and
   the **Create URL** button. See [Creating URLs](creating-urls.md). The new URL is copied to the clipboard.
3. **Folder import**: the *Import shares_\*.json from Downloads* switch. See below.
4. **Config (shares.json)**: the raw config in an editor, with **Save config**.

## Staying alive

Tunnels are served by a **foreground service** (type `dataSync`) that shows a low-priority "Tunnels running"
notification. As long as that notification is present the system will not freeze the app. Allow notifications when
asked; if you deny them the service still runs on most Android versions but may be stopped sooner.

!!! tip "Battery optimisation"
    Some vendors (Xiaomi, Huawei, Samsung "deep sleep") kill foreground services anyway. Exclude Zorek from battery
    optimisation in system settings if tunnels stop after a while.

The service restarts itself (`START_STICKY`) after the system kills it, and the app re-reads the config on start.
It does **not** start at boot (no `RECEIVE_BOOT_COMPLETED`): open the app once after a reboot.

## Reaching the target

`tunnel_ip` is resolved **from the phone**:

- a LAN device: its LAN address (`192.168.1.20`); the phone must be on that network;
- a server on the same phone: `127.0.0.1`;
- on the **Android emulator**, the host PC is `10.0.2.2` (not `127.0.0.1`).

## Import shares_*.json from Downloads

Turn the switch on to have Zorek watch the public **Downloads** folder for files named `shares_*.json`, and merge
every new one into the config. Typical flow: create URLs on your PC, send yourself `shares_home.json`, download it on
the phone, and the tunnels appear. Details of the merge rules are in [Importing shares files](importing.md).

Reading other apps' files in Downloads needs the **All files access** permission. When you turn the switch on and the
permission is missing, Zorek opens the system settings page for it; allow it for Zorek and come back. Without it the
folder simply looks empty and nothing is imported.

The switch is remembered across restarts and takes effect immediately; files already in Downloads when you turn it on
are imported on the next 2-second tick.

## Logs

Everything Zorek prints goes to logcat with the tag `python.stderr`:

```
adb logcat -s python.stderr
tunnel 74er67ijxyd8: listening
tunnel 74er67ijxyd8: connection
```

## Updating

Install the new APK over the old one: the config, remembered token and identities live in the app's private storage
and survive the update. Uninstalling the app deletes them.

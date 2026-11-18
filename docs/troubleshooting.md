# Troubleshooting

First look at the **State** column (PC) or the status line (Android): it shows `running` or the last error of each
tunnel, and a red line for config/import errors. Details are printed to stderr (PC: the console in `--nogui` mode;
Android: `adb logcat -s python.stderr`).

## The public URL shows "zrok - bad gateway"

The frontend found no one serving the share.

- The tunnel is not running: check its state. Not listed at all? The entry is missing from the config or the config is
  invalid (red error line).
- The state is `ValueError('negative file descriptor')` or the tunnel keeps restarting: the identity used cannot bind
  this share. **Only the zrok environment that created a share can serve it.** Put the right `identity` on the entry (see
  [identity resolution](config.md#identity-resolution)); a freshly enabled environment cannot take over shares created
  elsewhere.
- The same share is bound on another device: stop it there.
- Just started? Give it 5-10 seconds after the first `listening`.

## State: `connecting` for a long time

The tunnel thread is still loading its ziti identity. Identities are loaded **one at a time**, and loading the identity of
an environment that was **disabled or deleted** in zrok never finishes: it blocks, silently, and every tunnel behind it
shows `connecting` (the app itself stays responsive). Find the share whose environment you deleted (the zrok console
shows which environments exist) and remove its entry, or put the identity of a live environment on it. The rest start
by themselves once the entry is gone and the app is restarted.

## State: `cannot reach 10.0.0.5:80: ...`

The tunnel is fine; the **target** refused or timed out when a visitor arrived.

- Is the service up, on that port, and listening on a non-loopback address if it is on another machine?
- A firewall on the target machine (for the Windows host: allow inbound for the program that listens).
- Android emulator: the host PC is `10.0.2.2`, not `127.0.0.1`.
- `https` target answered with plain HTTP (or vice versa): fix `tunnel_scheme`.

## Create URL fails

The message is the HTTP status of the zrok call, verbatim.

| Message contains | Meaning |
|------------------|---------|
| `enable token required` | nothing typed and no `enable_token` in the config / `ZROK2_ENABLE_TOKEN` |
| `HTTP 401` | wrong or revoked token, or the environment in the config was disabled/deleted. Remove `identity`/`env_zid` from the entries (or use a fresh config) to enable a new environment |
| `HTTP 409` | the public name is already taken; choose another |
| `HTTP 429` | too many requests (typically many *enables* in a row): wait a few minutes |
| `HTTP 5xx` or a network error | zrok service or connectivity problem; retry |

If a failure happens after the name was reserved but before the share was created, the name stays reserved in your
account; delete it in the zrok console.

## Android: nothing happens / tunnels stop

- No notification = service mode is off (or you pressed **Stop**): open the app and turn *Service mode* on.
- Nothing after a reboot: turn on *Start service mode on boot*; some vendors also need *auto-start* allowed for Zorek (see [Android app](android.md#start-on-boot)).
- Tunnels die after a while: exclude the app from battery optimisation (see [Android app](android.md#start-on-boot)).
- Stuck on "starting...": check `adb logcat -s python.stderr AndroidRuntime`.
- The phone must reach the target: a LAN device needs the phone on that Wi-Fi.

## Import does not pick up my file

- The name must match `shares_*.json` exactly (case-sensitive on Android).
- Android: the switch must be on **and** *All files access* granted to Zorek.
- Overwrite with the same content and time? Zorek remembers `name:mtime:size`; touch or change the file.
- Invalid JSON: the file name and the parse error show in the red line.
- To force a re-import, delete `shares.json.imported` next to the config.

## Browsers show a warning page

On the shared `shares.zrok.io` domain zrok may show an interstitial page to browsers. Non-browser clients can send the
header `skip_zrok_interstitial: 1`.

## Console noise when stopping

When a tunnel is stopped or a share is deleted, libziti may log lines like `NOT_FOUND ... edge-routers` or
`service not available`. They are expected during teardown and harmless.

## Still stuck

Open an issue at <https://github.com/mon231/com.rel.zorek/issues> with the state/error text and the relevant log lines.
**Do not attach your `shares.json`**: it contains secrets (see [Security](security.md)).

# Security

Zorek publishes a service from your network to the internet, and stores credentials to do so. Read this page before
exposing anything sensitive.

## What is exposed

- A public URL reaches the target with **no authentication** (shares are created with `authScheme: none`). Anyone who
  learns the URL can talk to `tunnel_ip:tunnel_port`. Names are guessable if you choose short ones; the random default
  (`zorek` + 8 hex digits) is not, but is not secret either (it appears in browser history, logs, referrers).
- Add authentication **in the target** (basic auth, login page, API key), or put something in front of it.
- Do not tunnel services that were never meant to face the internet (databases, admin panels, SSH) without protection.
- Zorek forwards to *any* `tunnel_ip` you write, including addresses on other machines of your LAN. Whoever can edit
  your config can make your device reach into your network.

## What is stored, in plain text

| Secret | Where | Power |
|--------|-------|-------|
| `enable_token` | `shares.json` | create/delete shares and environments in your zrok account |
| `identity` (ziti private key) | `shares.json`, `~/.zrok2/identities/zorek-*.json`, `shares_*.json` files | impersonate the environment: bind its shares |

Consequences:

- **Do not commit or share `shares.json`** or any `shares_*.json` file, and do not paste them into chats or issues.
- `shares_*.json` files you move between devices contain the private key: delete them after use, and prefer a direct
  cable/transfer over cloud storage.
- The Android editor **shows the whole config** on screen, including the key. Mind screen sharing.
- On Android the files live in the app's private storage, which other apps cannot read. The app sets
  `allowBackup="false"`, so they are not included in device backups. A rooted device can read them.
- On PC, `~/.zrok2` and your config are as private as your user account: set file permissions accordingly on a shared
  machine.

!!! tip "If a secret leaks"
    Open the zrok web console, **disable** the environment (this revokes its identity) and, if the account token
    leaked, rotate the token. Then create the shares again.

## Transport

- Visitor to the zrok frontend: HTTPS, terminated by the zrok service. **zrok can see the plain HTTP traffic.**
  Zorek does not add end-to-end encryption between the visitor and your target.
- zrok frontend to Zorek: the OpenZiti overlay, mutually authenticated with the identity.
- Zorek to the target: plain TCP, or TLS for `tunnel_scheme: https`. For `https` targets the **certificate is not
  verified** (hostname checking and chain validation are off), which is what makes self-signed LAN devices work. It also
  means a machine that impersonates the target on your LAN will be accepted.

## Android permissions

| Permission | Why |
|------------|-----|
| `INTERNET` | reach zrok and your targets |
| `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_SPECIAL_USE` | keep the tunnels running in the background (service mode) |
| `POST_NOTIFICATIONS` | show the status notification of the foreground service |
| `RECEIVE_BOOT_COMPLETED` | start service mode after a reboot; only acts if the *Start on boot* switch is on |
| `MANAGE_EXTERNAL_STORAGE` | **only used if you turn the Downloads import on**; lets Zorek read `shares_*.json` from the public Downloads folder. It grants broad file access, so turn the switch off (and revoke it in system settings) when you are not importing. |

## Supply chain

- The APK is signed with a fixed key (via `signapp`) so updates install over earlier versions.
- `libziti.so` is built in CI from the upstream ziti-sdk-c 1.18.3 source; the recipe is in `native/`.
- `openziti` is vendored (one-line patch, documented in `vendor/README.md`).

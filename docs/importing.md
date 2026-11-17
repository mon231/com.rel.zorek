# Importing shares files

You can hand shares to a Zorek instance by dropping a file named **`shares_<anything>.json`** into a watched folder.
This is the easy way to move URLs between your PC and your phone, or to give a device a set of shares without typing.

## Turning it on

| Where | How |
|-------|-----|
| Android | the **Import shares_\*.json from Downloads** switch (needs *All files access*, see [Android app](android.md#import-shares_json-from-downloads)). The folder is the public Downloads folder. |
| PC GUI | the **Watch** checkbox and folder box. Default folder: `~/Downloads`. |
| Python | `Zorek(config, import_dir="/some/folder")` or `z.set_import_dir(path)` / `z.set_import_dir(None)` |

It is a feature flag: when off, nothing in the folder is looked at.

## File format

A `shares_*.json` file has the same format as the [config](config.md): a plain list, or an object with `shares` and
optional `identity` / `env_zid`. Only the file name pattern matters: `shares_home.json`, `shares_2026-11.json`,
`shares_phone (1).json` are all picked up; `shares.json`, `myshares_a.json` and `shares_a.txt` are not.

## Merge rules

For every **new** file, in alphabetical order:

1. Each entry of the file inherits the file's top-level `identity` and `env_zid` if it has none of its own. This keeps
   every entry self-contained, so shares from different zrok environments can coexist in one config.
2. An entry whose `public_token` is already in the config **replaces** that entry; any other entry is **appended**.
3. The config is written atomically, and the tunnels follow within 2 seconds.

Nothing is ever removed from the config by an import, and the imported file is **not deleted or modified**.

## "New" means a new version of the file

Zorek remembers what it imported in `shares.json.imported`, as `name:modified-time:size`. So:

- a file is imported once, even though the folder is re-scanned every 2 seconds;
- if you **overwrite** the file with new content (different modification time or size), it is imported again;
- a file that cannot be read yet, typically because the browser is still downloading it, is skipped silently and
  retried on the next tick; a file that is permanently invalid is skipped and reported as an error without blocking the
  other files.

## Example: PC to phone

1. On the PC, create a URL (it is written to `shares.json`).
2. Copy that file to the phone as `shares_pc.json` (Downloads folder, via USB, a messenger, cloud storage...).
   It already contains the identity of the environment that owns the share.
3. On the phone, with the switch on, the tunnel appears in the app; the same public URL now forwards to whatever
   `tunnel_ip` you wrote in it (edit the file before sending it: for a PC server use the PC's LAN address).

!!! warning "The file contains a private key"
    Entries carry the ziti identity, which includes a private key. Send `shares_*.json` only over channels you trust and
    delete it when done. See [Security](security.md).

!!! note "One URL, one place"
    A share can be served by one Zorek instance at a time. If the same share is bound on the PC and on the phone,
    requests go to one of them unpredictably. Stop the tunnel on one device (remove the entry) when you move it.

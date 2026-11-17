"""Minimal zrok v2 API client over urllib (the zrok2 SDK needs pydantic-core, which has no Android build)."""
import json
import os
import socket
import urllib.error
import urllib.request


def _call(method, path, token, body=None):
    api = os.environ.get("ZROK2_API_ENDPOINT", "https://api-v2.zrok.io").rstrip("/")
    req = urllib.request.Request(
        f"{api}/api/v2{path}", method=method, data=None if body is None else json.dumps(body).encode(),
        headers={"x-token": token, "Content-Type": "application/zrok.v1+json",
                 "Accept": "application/json, application/zrok.v1+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"zrok {method} {path}: HTTP {e.code} {e.read()[:200].decode(errors='replace')}") from None
    return json.loads(raw) if raw else {}


def enable(token):
    """zrok `enable`: new environment. Returns {"identity": <ziti identity dict>, "env_zid": <environment id>}."""
    res = _call("POST", "/enable", token, {"host": socket.gethostname(), "description": "zorek"})
    return {"identity": json.loads(res["cfg"]), "env_zid": res["identity"]}


def create_share(token, env_zid, name):
    """Reserve `name` in the default namespace and create a public proxy share on it. Returns (share_token, url)."""
    ns = _call("GET", "/share/namespaces", token)[0]["namespaceToken"]
    _call("POST", "/share/name", token, {"namespaceToken": ns, "name": name})
    res = _call("POST", "/share", token, {
        "envZId": env_zid, "shareMode": "public", "backendMode": "proxy", "target": "http://tunnel",
        "authScheme": "none", "nameSelections": [{"namespaceToken": ns, "name": name}]})
    url = res["frontendProxyEndpoints"][0]
    return res["shareToken"], url if "://" in url else "https://" + url

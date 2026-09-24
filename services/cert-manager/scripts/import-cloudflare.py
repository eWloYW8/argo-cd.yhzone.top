#!/usr/bin/env python3
"""Import the existing Caddy Cloudflare token without printing or committing it."""
import json
from pathlib import Path
import subprocess
import yaml
compose = yaml.safe_load((Path.home() / "docker/caddy/docker-compose.yml").read_text())
env = compose["services"]["caddy"]["environment"]
if isinstance(env, list):
    env = dict(item.split("=", 1) for item in env if "=" in item)
token = env["CLOUDFLARE_API_TOKEN"]
assert token
secret = {"apiVersion": "v1", "kind": "Secret",
          "metadata": {"name": "cloudflare-api-token", "namespace": "cert-manager"},
          "type": "Opaque", "stringData": {"api-token": token}}
result = subprocess.run(["kubectl", "--context", "yihao", "apply", "--server-side",
                         "--field-manager=yihao-bootstrap", "-f", "-"],
                        input=json.dumps(secret), text=True, capture_output=True)
if result.returncode:
    raise SystemExit("Cloudflare Secret import failed; output suppressed")
print("Cloudflare Secret imported.")

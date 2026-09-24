#!/usr/bin/env python3
"""Seed missing Harbor secrets once; never rotate an existing database password."""
import json
from pathlib import Path
import secrets
import string
import subprocess
import tempfile
import bcrypt

K = ["kubectl", "--context", "yihao"]
def exists(name):
    result = subprocess.run(K + ["-n", "harbor", "get", "secret", name, "--ignore-not-found", "-o", "name"], text=True, capture_output=True, check=True)
    return bool(result.stdout.strip())
def seed(name, data, secret_type="Opaque"):
    obj = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": name, "namespace": "harbor"}, "type": secret_type, "stringData": data}
    result = subprocess.run(K + ["apply", "--server-side", "--field-manager=yihao-bootstrap", "-f", "-"], input=json.dumps(obj), text=True, capture_output=True)
    if result.returncode:
        raise SystemExit("Secret creation failed; response suppressed")
    print("Created " + name)
def random_string(length):
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

if not exists("harbor-bootstrap"):
    # Existing PVCs require restoration of their original credentials instead.
    claims = json.loads(subprocess.check_output(K + ["-n", "harbor", "get", "pvc", "-o", "json"]))
    if claims["items"]:
        raise SystemExit("Existing Harbor PVCs found: restore original secrets from backup")
    password, registry_password = random_string(40), random_string(40)
    seed("harbor-bootstrap", {
        "HARBOR_ADMIN_PASSWORD": random_string(40), "secretKey": random_string(16),
        "secret": random_string(16), "CSRF_KEY": random_string(32),
        "JOBSERVICE_SECRET": random_string(16), "REGISTRY_HTTP_SECRET": random_string(16),
        "REGISTRY_PASSWD": registry_password,
        "REGISTRY_HTPASSWD": "harbor_registry_user:" + bcrypt.hashpw(registry_password.encode(), bcrypt.gensalt()).decode(),
        "password": password, "POSTGRES_PASSWORD": password,
    })
if not exists("harbor-token-signing"):
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory)
        subprocess.run(["openssl", "genrsa", "-traditional", "-out", str(p / "key"), "3072"], capture_output=True, check=True)
        subprocess.run(["openssl", "req", "-new", "-x509", "-key", str(p / "key"), "-out", str(p / "crt"), "-days", "3650", "-subj", "/CN=harbor-token-signing"], capture_output=True, check=True)
        seed("harbor-token-signing", {"tls.key": (p / "key").read_text(), "tls.crt": (p / "crt").read_text()}, "kubernetes.io/tls")

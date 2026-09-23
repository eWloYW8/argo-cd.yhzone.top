#!/usr/bin/env python3
"""Configure Argo CD HTTPS credentials without exposing the token in argv or Git."""
import getpass
import json
import os
from pathlib import Path
import subprocess

source = os.environ.get("ARGOCD_TOKEN_FILE")
token = Path(source).read_text().strip() if source else getpass.getpass("Argo CD read-only GitHub token: ")
if not token:
    raise SystemExit("Token is empty")
secret = {
    "apiVersion": "v1", "kind": "Secret",
    "metadata": {"name": "yihao-git-repository", "namespace": "argocd",
                 "labels": {"argocd.argoproj.io/secret-type": "repository"}},
    "type": "Opaque",
    "stringData": {"type": "git", "url": "https://github.com/eWloYW8/argo-cd.yhzone.top.git",
                   "username": "eWloYW8", "password": token},
}
subprocess.run(["kubectl", "--context", "yihao", "apply", "--server-side", "--field-manager=yihao-bootstrap", "-f", "-"],
               input=json.dumps(secret), text=True, check=True)

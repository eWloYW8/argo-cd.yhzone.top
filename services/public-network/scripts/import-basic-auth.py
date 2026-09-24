#!/usr/bin/env python3
"""Copy one explicit Caddy Basic Auth block to a Kubernetes Secret, without logging credentials."""
import argparse
import base64
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--caddyfile', type=Path, default=Path.home() / 'docker/caddy/Caddyfile')
parser.add_argument('--site', required=True, help='Exact Caddy site address, including scheme and port')
parser.add_argument('--namespace', required=True)
parser.add_argument('--secret', default='public-basic-auth')
args = parser.parse_args()
lines = args.caddyfile.read_text().splitlines()
site = None
blocks = []
for i, line in enumerate(lines):
    if line and not line[0].isspace() and line.rstrip().endswith('{'):
        site = line.strip()[:-1].strip()
    if site != args.site or not re.fullmatch(r'\s*(basic_auth|basicauth)\s*\{\s*', line):
        continue
    users = []
    for entry in lines[i + 1:]:
        if entry.strip() == '}':
            break
        if not entry.strip() or entry.lstrip().startswith('#'):
            continue
        fields = entry.split()
        if len(fields) != 2 or not re.fullmatch(r'\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}', fields[1]):
            raise SystemExit('Unsupported credential format; expected username and bcrypt hash')
        users.append(':'.join(fields))
    if not users:
        raise SystemExit('Selected Basic Auth block is empty')
    blocks.append(users)
if len(blocks) != 1:
    raise SystemExit('Expected exactly one Basic Auth block for the selected site')
secret = {
    'apiVersion': 'v1', 'kind': 'Secret', 'type': 'Opaque',
    'metadata': {'name': args.secret, 'namespace': args.namespace},
    'data': {'users': base64.b64encode(('\n'.join(blocks[0]) + '\n').encode()).decode()},
}
subprocess.run(['kubectl', '--context', 'yihao', 'apply', '--server-side',
                '--field-manager=basic-auth-bootstrap', '-f', '-'],
               input=json.dumps(secret), text=True, check=True)
print('Imported bcrypt credentials without copying plaintext passwords.')

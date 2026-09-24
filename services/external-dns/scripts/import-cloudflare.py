#!/usr/bin/env python3
"""Copy the existing cert-manager Cloudflare credential without exposing it."""
import json
import subprocess

kubectl = ['kubectl', '--context', 'yihao']
source = json.loads(subprocess.check_output(kubectl + [
    '-n', 'cert-manager', 'get', 'secret', 'cloudflare-api-token', '-o', 'json']))
resources = [
    {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': 'external-dns'}},
    {'apiVersion': 'v1', 'kind': 'Secret',
     'metadata': {'name': 'cloudflare-api-token', 'namespace': 'external-dns'},
     'type': 'Opaque', 'data': {'api-token': source['data']['api-token']}},
]
for resource in resources:
    result = subprocess.run(kubectl + ['apply', '--server-side',
        '--field-manager=yihao-bootstrap', '-f', '-'],
        input=json.dumps(resource), text=True, capture_output=True)
    if result.returncode:
        raise SystemExit('Cloudflare credential import failed; output suppressed')
print('Cloudflare credential imported into external-dns.')

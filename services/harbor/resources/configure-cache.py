"""Reconcile declared upstream caches without storing credentials in Git."""
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

base = 'http://harbor.harbor.svc.cluster.local/api/v2.0'
auth = base64.b64encode(('admin:' + os.environ['HARBOR_ADMIN_PASSWORD']).encode()).decode()

def api(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(base + path, data=data, method=method,
        headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
        return json.loads(body) if body else None

config = json.loads(Path('/scripts/cache-config.json').read_text())
assert sum(p['quotaGiB'] for p in config['projects']) == 30
for attempt in range(90):
    try:
        registries = api('GET', '/registries?page_size=100')
        break
    except (urllib.error.URLError, TimeoutError):
        if attempt == 89:
            raise
        time.sleep(5)
for desired in config['registries']:
    registry = next((r for r in registries if r['name'] == desired['name']), None)
    if registry is None:
        api('POST', '/registries', dict(desired, insecure=False))
        registries = api('GET', '/registries?page_size=100')
    else:
        assert registry['type'] == desired['type'] and registry['url'].rstrip('/') == desired['url'].rstrip('/'), 'Upstream mismatch: ' + desired['name']
registries = {r['name']: r for r in registries}
for desired in config['projects']:
    name = desired['name']
    registry_id = registries[desired['registry']]['id']
    path = '/projects?name=' + urllib.parse.quote(name, safe='')
    project = next((p for p in api('GET', path) if p['name'] == name), None)
    if project is None:
        api('POST', '/projects', {'project_name': name, 'registry_id': registry_id,
            'public': desired['public'], 'storage_limit': desired['quotaGiB'] * 1024**3})
        project = next(p for p in api('GET', path) if p['name'] == name)
    assert project['registry_id'] == registry_id, 'Proxy cache mismatch: ' + name
    api('PUT', '/projects/' + str(project['project_id']),
        {'metadata': {'public': str(desired['public']).lower()}})
    quotas = api('GET', '/quotas?reference=project&reference_id=' + str(project['project_id']))
    assert len(quotas) == 1
    limit = desired['quotaGiB'] * 1024**3
    assert quotas[0]['used']['storage'] <= limit, 'Existing cache exceeds new quota: ' + name
    api('PUT', '/quotas/' + str(quotas[0]['id']), {'hard': {'storage': limit}})
    print(name + ': proxy configured, quota ' + str(desired['quotaGiB']) + ' GiB, public=' + str(desired['public']))
print('Declared cache quotas total 30 GiB.')

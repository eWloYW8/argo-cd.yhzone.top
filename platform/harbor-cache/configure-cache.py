import os, json, time, base64, urllib.request, urllib.error
base = 'http://harbor.harbor.svc.cluster.local/api/v2.0'
auth = base64.b64encode(('admin:' + os.environ['HARBOR_ADMIN_PASSWORD']).encode()).decode()
def api(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(base + path, data=data, method=method, headers={'Authorization': 'Basic ' + auth, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as response:
        body = response.read()
        return json.loads(body) if body else None
for attempt in range(90):
    try:
        registries = api('GET', '/registries?page_size=100')
        break
    except (urllib.error.URLError, TimeoutError):
        if attempt == 89: raise
        time.sleep(5)
registry = next((x for x in registries if x['name'] == 'dockerhub'), None)
if registry is None:
    api('POST', '/registries', {'name': 'dockerhub', 'type': 'docker-hub', 'url': 'https://hub.docker.com', 'insecure': False})
    registry = next(x for x in api('GET', '/registries?page_size=100') if x['name'] == 'dockerhub')
projects = api('GET', '/projects?name=dockerhub')
project = next((x for x in projects if x['name'] == 'dockerhub'), None)
if project is None:
    api('POST', '/projects', {'project_name': 'dockerhub', 'registry_id': registry['id'], 'public': False, 'storage_limit': 30 * 1024**3})
    project = next(x for x in api('GET', '/projects?name=dockerhub') if x['name'] == 'dockerhub')
assert project['registry_id'] == registry['id'], 'Existing project is not the expected proxy cache'
quotas = api('GET', '/quotas?reference=project&reference_id=' + str(project['project_id']))
assert len(quotas) == 1
api('PUT', '/quotas/' + str(quotas[0]['id']), {'hard': {'storage': 30 * 1024**3}})
print('Docker Hub private proxy cache configured; quota 30 GiB.')

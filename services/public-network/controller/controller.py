"""Reconcile opt-in public Ingress DNS and SNI routes. No Cloudflare credentials."""
import datetime
import hashlib
import ipaddress
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GROUP = 'networking.yhzone.top'
LABEL = GROUP + '/managed-by'
MANAGER = 'public-network-controller'
NS = os.getenv('NAMESPACE', 'public-network')
IPV4 = os.getenv('PUBLIC_IPV4', '101.37.69.162')
IPV4_NODE = os.getenv('IPV4_NODE', 'ali-sas')
HOST_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.yhzone\.top$')


def ready(obj):
    return any(c.get('type') == 'Ready' and c.get('status') == 'True'
               for c in obj.get('status', {}).get('conditions', []))


def authorized_addresses(resources, nodes):
    result = {}
    for r in resources:
        name = r['metadata']['name']
        if name not in nodes or not r.get('spec', {}).get('enabled', True):
            continue
        try:
            addr = ipaddress.IPv6Address(r['spec']['address'])
            if addr in ipaddress.IPv6Network('2000::/3') and addr.is_global:
                result[name] = str(addr)
        except (ValueError, KeyError):
            pass
    return result


def public_ingress(ing):
    m = ing['metadata']
    return (ing.get('spec', {}).get('ingressClassName') == 'traefik-public'
            and m.get('labels', {}).get(GROUP + '/exposure') == 'public')


def calculate(ingresses, services, slices, nodes, addresses, gateway_nodes, certificates):
    """Pure reconciliation: AAAA is intersection of ready backend nodes for each host."""
    services = {(s['metadata']['namespace'], s['metadata']['name']): s for s in services}
    endpoint_nodes = {}
    for s in slices:
        key = (s['metadata']['namespace'], s['metadata'].get('labels', {}).get('kubernetes.io/service-name'))
        for e in s.get('endpoints', []):
            n = e.get('nodeName')
            if (n and e.get('conditions', {}).get('ready') is True
                    and not e.get('conditions', {}).get('terminating', False)):
                endpoint_nodes.setdefault(key, set()).add(n)
    certs = {(c['metadata']['namespace'], c.get('spec', {}).get('secretName')): c
             for c in certificates if ready(c)}
    domains, routes = {}, set()
    conflicts = set()
    for ing in ingresses:
        if not public_ingress(ing):
            continue
        m, spec = ing['metadata'], ing['spec']
        ns = m['namespace']
        for rule in spec.get('rules', []):
            host = rule.get('host', '')
            if not HOST_RE.fullmatch(host):
                continue
            routes.add(host)
            if m.get('annotations', {}).get(GROUP + '/publish-dns', 'true') != 'true':
                continue
            if not any(host in t.get('hosts', []) and (ns, t.get('secretName')) in certs
                       and host in certs[(ns, t['secretName'])]['spec'].get('dnsNames', [])
                       for t in spec.get('tls', [])):
                continue
            backends = [p.get('backend', {}).get('service', {}).get('name')
                        for p in rule.get('http', {}).get('paths', [])]
            if not backends or any(not b or (ns, b) not in services for b in backends):
                continue
            if host in domains:
                conflicts.add(host)
                continue
            common = set.intersection(*(endpoint_nodes.get((ns, b), set()) for b in backends))
            # Native service LB + PreferSameNode preserves node-local preference; otherwise IPv4 only.
            local_routing = all(services[(ns, b)].get('spec', {}).get('trafficDistribution') == 'PreferSameNode'
                and services[(ns, b)]['metadata'].get('annotations', {}).get(
                    'traefik.ingress.kubernetes.io/service.nativelb') == 'true' for b in backends)
            v6 = sorted({addresses[n] for n in common if n in addresses and n in gateway_nodes
                         and ready(nodes.get(n, {}))}) if local_routing else []
            records = []
            if IPV4_NODE in gateway_nodes and ready(nodes.get(IPV4_NODE, {})):
                records.append({'dnsName': host, 'recordType': 'A', 'recordTTL': 120, 'targets': [IPV4]})
            if v6:
                records.append({'dnsName': host, 'recordType': 'AAAA', 'recordTTL': 120, 'targets': v6})
            if records:
                domains[host] = records
    for host in conflicts:
        domains.pop(host, None)
    return domains, sorted(routes)


def haproxy_config(hosts):
    # Hostnames validated before interpolation; public internal domains never reach legacy fallback.
    lines = ['global', '  log stdout format raw local0', '  maxconn 2048', '  nbthread 1',
             'defaults', '  mode tcp', '  log global', '  timeout connect 10s',
             '  timeout client 1h', '  timeout server 1h',
             'frontend tls', '  bind ":::${PUBLIC_PORT}" v4v6',
             '  tcp-request inspect-delay 5s',
             r'  tcp-request content reject if { req.ssl_sni -m reg -i \.k8s\.yhzone\.top\.?$ }',
             '  tcp-request content accept if { req.ssl_hello_type 1 }']
    if hosts:
        lines.extend(['  acl kubernetes_public req.ssl_sni -i ' + ' '.join(hosts),
                      '  use_backend kubernetes if kubernetes_public'])
    lines.extend(['  default_backend legacy', 'backend kubernetes',
                  '  server local 127.0.0.1:20444 send-proxy-v2',
                  'backend legacy', '  server legacy 127.0.0.1:21443'])
    return '\n'.join(lines) + '\n'


class API:
    def __init__(self):
        self.base = 'https://' + os.environ['KUBERNETES_SERVICE_HOST'] + ':' + os.getenv('KUBERNETES_SERVICE_PORT', '443')
        self.sa = Path('/var/run/secrets/kubernetes.io/serviceaccount')
        self.context = ssl.create_default_context(cafile=str(self.sa / 'ca.crt'))
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=self.context))

    def call(self, method, path, data=None):
        headers = {'Authorization': 'Bearer ' + (self.sa / 'token').read_text().strip()}
        if data is not None:
            headers['Content-Type'] = 'application/merge-patch+json' if method == 'PATCH' else 'application/json'
        req = urllib.request.Request(self.base + path, method=method, headers=headers,
                                     data=json.dumps(data).encode() if data is not None else None)
        with self.opener.open(req, timeout=20) as r:
            return json.load(r)

    def listing(self, path):
        result, cursor = [], ''
        while True:
            page = self.call('GET', path + ('&' if '?' in path else '?') + urllib.parse.urlencode({'limit': 500, 'continue': cursor}))
            result.extend(page['items'])
            cursor = page.get('metadata', {}).get('continue', '')
            if not cursor:
                return result


def reconcile(api):
    nodes = {n['metadata']['name']: n for n in api.listing('/api/v1/nodes')}
    resources = api.listing('/apis/' + GROUP + '/v1alpha1/nodepublicipv6s')
    addresses = authorized_addresses(resources, nodes)
    label = GROUP + '/public-gateway'
    for name, node in nodes.items():
        # Retain enrolled gateways for cached DNS and legacy connections; removal is an operator action.
        wanted = 'true' if name == IPV4_NODE or name in addresses else node['metadata'].get('labels', {}).get(label)
        if node['metadata'].get('labels', {}).get(label) != wanted:
            api.call('PATCH', '/api/v1/nodes/' + name, {'metadata': {'labels': {label: wanted}}})
    pods = api.listing('/api/v1/namespaces/' + NS + '/pods?labelSelector=app.kubernetes.io/name%3Dtraefik')
    gateways = {p['spec']['nodeName'] for p in pods if ready(p) and not p['metadata'].get('deletionTimestamp')}
    ingresses = api.listing('/apis/networking.k8s.io/v1/ingresses')
    services = api.listing('/api/v1/services')
    slices = api.listing('/apis/discovery.k8s.io/v1/endpointslices')
    certs = api.listing('/apis/cert-manager.io/v1/certificates')
    domains, hosts = calculate(ingresses, services, slices, nodes, addresses, gateways, certs)
    path = '/api/v1/namespaces/' + NS + '/configmaps/public-edge-routes'
    try:
        current = api.call('GET', path)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        current = api.call('POST', '/api/v1/namespaces/' + NS + '/configmaps',
            {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'public-edge-routes', 'namespace': NS, 'labels': {LABEL: MANAGER}}, 'data': {'haproxy.cfg': haproxy_config(hosts)}})
    config = haproxy_config(hosts)
    if current.get('data', {}).get('haproxy.cfg') != config:
        api.call('PATCH', path, {'data': {'haproxy.cfg': config}})
        print('Updated SNI routes: ' + ','.join(hosts), flush=True)
    endpoint_path = '/apis/externaldns.k8s.io/v1alpha1/namespaces/' + NS + '/dnsendpoints'
    existing = {r['metadata']['name']: r for r in api.listing(endpoint_path)
                if r['metadata'].get('labels', {}).get(LABEL) == MANAGER}
    desired = set()
    for host, records in domains.items():
        name = 'public-' + hashlib.sha256(host.encode()).hexdigest()[:16]
        desired.add(name)
        body = {'apiVersion': 'externaldns.k8s.io/v1alpha1', 'kind': 'DNSEndpoint',
                'metadata': {'name': name, 'namespace': NS, 'labels': {LABEL: MANAGER, GROUP + '/dns-scope': 'public'}},
                'spec': {'endpoints': records}}
        if name not in existing:
            api.call('POST', endpoint_path, body)
        elif existing[name].get('spec') != body['spec']:
            api.call('PATCH', endpoint_path + '/' + name, {'spec': body['spec']})
    # All lists must succeed before garbage collection. Never delete unowned objects.
    for name in set(existing) - desired:
        api.call('DELETE', endpoint_path + '/' + name)
    for r in resources:
        name = r['metadata']['name']
        state = 'Ready' if name in addresses and name in gateways and ready(nodes.get(name, {})) else 'NotReady'
        status = {'observedGeneration': r['metadata'].get('generation', 1), 'phase': state,
                  'publishedHosts': sorted(h for h, records in domains.items()
                      if any(x['recordType'] == 'AAAA' and addresses.get(name) in x['targets'] for x in records))}
        if r.get('status') != status:
            api.call('PATCH', '/apis/' + GROUP + '/v1alpha1/nodepublicipv6s/' + name + '/status', {'status': status})


if __name__ == '__main__':
    api = API()
    while True:
        try:
            reconcile(api)
            Path('/tmp/last-success').touch()
        except Exception as exc:
            # No API response bodies or credentials in logs.
            print('Reconciliation failed: ' + type(exc).__name__ + ' ' + str(getattr(exc, 'code', '')), flush=True)
        time.sleep(10)

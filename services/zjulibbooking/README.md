# ZJULibBooking

Local Helm chart, deployed through the `zjulibbooking` Argo CD Application.

- Public: https://zjulib.yhzone.top:20443
- EasyTier: https://zjulib.k8s.yhzone.top
- Legacy: https://zjulib.d.yhzone.top:20443 remains served by the legacy Caddy SNI fallback, proxying over verified HTTPS to the Kubernetes internal Ingress. This preserves the browser origin and its saved form values.

The image is the original Docker runtime image (source revision `be0066188b5adfbf220d4d97e4a5db519f82aa45`), preserved in the private Harbor project `zjulibbooking` and pinned by digest. It is amd64 only. `harbor-pull` is an out-of-Git dockerconfigjson Secret backed by a project-scoped pull-only robot account. The normal image-prefix component adds `harbor.k8s.yhzone.top/`; this is a hosted image project, not an upstream proxy cache.

The original application has no database or persistent files. Form settings are browser localStorage; live booking tasks exist only in Python process memory. Changing origin does not transfer localStorage. Pod restarts or upgrades discard active tasks; recreate tasks in the UI when needed. A single replica with Recreate strategy prevents concurrent old/new task managers. No PVC is allocated because it would not make the application's in-memory tasks persistent. Future durable state should use `yihao-local` under the configured `~/k8s/storage` root.

Public DNS and SNI routing are managed by `public-network`: IPv4 uses ali-sas, and AAAA is published only when the Ready backend node has its manually registered NodePublicIPv6 and Ready gateway. TLS is issued by cert-manager with the existing Cloudflare DNS01 ClusterIssuer.

Migration source and rollback container remain at `~/docker/ZJULibBooking`; the old Docker container is stopped and restart disabled and Compose placed behind the `legacy-rollback` profile after verification. Host-side migration backups are outside Git at `~/k8s/.bootstrap/zjulibbooking`. Do not start the old container while Kubernetes is serving booking tasks. For rollback, first pause this Argo application's automated sync and scale its Deployment to zero, restore the backed-up legacy Caddy site and Compose restart policy, then restart Docker. Public new-domain traffic also needs to be redirected or withdrawn during a rollback.

## Migration verification (2026-09-24)

Argo CD Synced/Healthy; one Ready Pod; both certificates Ready. Page and health endpoint returned HTTP 200 with system CA verification over the internal ingress, ali-sas public IPv4 and the first node global IPv6 address. IPv6 was tested from the first node, not from an independent external IPv6 network. Cloudflare contains internal A=10.1.2.4, public A=101.37.69.162 and public AAAA=2001:da8:e000:731a:be24:11ff:fe21:c6f6. Legacy health remained HTTP 200 after the Docker container was stopped. No actual library booking was submitted during verification.

## Public Basic Auth

Both public hostnames require the same Basic Auth account (`yihao`). The new Ingress references a Traefik Middleware backed by `zjulibbooking/public-basic-auth` (bcrypt `users` data, no plaintext); the legacy Caddy site uses the same bcrypt entry. The internal hostname remains accessible without this extra authentication. Harbor authentication is unchanged. The middleware strips the Authorization header before forwarding to the booking application.

Credentials are provisioned outside Git. Restore the Secret from a cluster backup, or import the current legacy site hash without printing it:

```sh
python3 services/public-network/scripts/import-basic-auth.py \
  --site https://zjulib.d.yhzone.top:21443 --namespace zjulibbooking
```

When rotating credentials, update both the Kubernetes Secret and the legacy Caddy site's bcrypt entry, then reload Caddy. No booking Pod restart is required.

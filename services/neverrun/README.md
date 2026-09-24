# NeverRun

Local Helm chart, managed by the `neverrun` Argo CD Application.

- Public: https://neverrun.yhzone.top:20443 (existing Caddy Basic Auth credentials, migrated into `neverrun/public-basic-auth`).
- EasyTier: https://neverrun.k8s.yhzone.top (no additional Basic Auth).
- Retired after cutover: `neverrun.d.yhzone.top:20443`. The shared `*.d.yhzone.top` wildcard remains for unrelated services.

Single amd64 replica on the first node, Recreate strategy. No database or persistent volume existed in Docker. Requests and streamed submissions are handled by the running process; browser state does not automatically move between origins. No PVC is needed.

The original `neverrun-neverrun` image was preserved locally. The migration image in the private Harbor project `neverrun` changes only removal of `print(password)` in `/app/server.py` and Python logging/bytecode environment flags. `image/Dockerfile` documents this patch; it does not update dependencies. The original image config ID is `sha256:576f0b1f2cbd56c0ced85d02f6de0cc0174997b9d3113aaa2db1cbdf2d353dfa`. Application source backups are private, outside Git, under `~/k8s/.bootstrap/neverrun`.

Secrets `harbor-pull` and `public-basic-auth` are bootstrapped outside Git. Back up both. The Basic Auth middleware strips the Authorization header before proxying. Internal and public TLS use the Cloudflare DNS01 ClusterIssuer. Public A/AAAA follow the cluster's existing manual NodePublicIPv6 eligibility rules.

Probes use `/openapi.json`, without logging into upstream services or submitting sport records. Validation must not create real sport submissions. The original Docker container is retained stopped, with restart disabled and Compose behind `legacy-rollback`. A rollback must stop the Kubernetes instance before reactivating the original container and restoring its old Caddy site from the private backup.

## Migration validation (2026-09-24)

Argo CD Synced/Healthy, one Ready Pod, both certificates Ready. Internal page and OpenAPI returned 200 with trusted TLS. Public IPv4 and local-node IPv6 rejected missing/invalid Basic Auth with 401; the Secret preserves the original Caddy bcrypt entries. No real login or sport submission was performed. The old Caddy site was removed and Docker stopped; the shared wildcard gateway may still return its generic fallback for the retired hostname. The application no longer contains the plaintext password print statement.

# Repository conventions

- Use Conventional Commits: `feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`, `chore(scope): ...`.
- Every kubectl mutation must explicitly select context `yihao`.
- Never commit credentials, tokens, private keys, rendered Secrets, or kubeconfigs.
- Pin chart/image versions. Deploy application resources through Argo CD.
- Store persistent application data with the `yihao-local` StorageClass.
- Validate changed Kustomize/Helm manifests before pushing.

## Service layout

- One service, one directory under `services/`, one generated Argo CD Application.
- Each directory has `app.yaml` (name, namespace, ignoreDifferences) and `kustomization.yaml` (the workload entrypoint).
- Use pinned upstream `helmCharts` and full, versioned `values/<chart>-<version>.yaml`; combine supplemental resources with Kustomize.
- Keep resources and service-specific scripts within the same service directory.
- Do not commit downloaded `charts/`; chart caches are ignored.
- `clusters/yihao` contains the root Application and ApplicationSet; ApplicationSet discovers `services/*/app.yaml`.
- `bootstrap/` contains only host/cluster bootstrap configuration.
- Validate using `kubectl kustomize --enable-helm services/<service>` before pushing. Do not print rendered Secrets.
- Never copy credentials or environment-specific networking from reference repositories.

## Default image registry

- Ordinary services include `../../components/image-prefix` in `components` to use `harbor.k8s.yhzone.top/<upstream>/<image>`.
- Normalize short Docker Hub names to `docker.io/library/<image>` (or `docker.io/<organization>/<image>`) before prefixing; verify rendered images have exactly one Harbor prefix.
- Bootstrap exceptions: Harbor and its database/setup Job, Traefik (internal/public), public-network controller/SNI edge, cert-manager, ExternalDNS (internal/public), local-path-provisioner, and K3s system components use upstream images to avoid circular dependencies.
- Proxy projects and their total 30 GiB quota are declared in `services/harbor/resources/cache-config.json`; see that service README before adding a registry.

## Public networking

- Internal Ingress class is `traefik`, domains `*.k8s.yhzone.top`, EasyTier-only port 443. Public class is `traefik-public`, opt-in label `networking.yhzone.top/exposure=public`, domains `<service>.yhzone.top`, port 20443.
- NodePublicIPv6 resources are manually authored; never add automatic IPv6 discovery/enrollment. AAAA requires the explicit resource, Ready node/gateway and Ready service backend on that node.
- Public backends use a separate Service with NativeLB annotation and `trafficDistribution: PreferSameNode`; public DNS is generated as DNSEndpoint, not via internal ExternalDNS annotations.
- Preserve legacy FRP/Caddy via the SNI fallback on 21443. Do not replace the public edge with a catch-all route to internal Ingress.

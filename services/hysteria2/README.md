# Hysteria2

Local Helm chart, managed by the `hysteria2` Argo CD Application. The original v2.7.0 amd64-avx binary and runtime are preserved in a private Harbor project and pinned by digest. The service remains pinned to `yihao-pve-debian`.

## Network compatibility

The single Recreate Deployment uses host networking and UDP 30443. IPv6 still connects directly. IPv4 now reaches the Argo CD-managed `hysteria2-udp-gateway` on ali-sas, which forwards UDP through the `hysteria2-udp` ClusterIP Service to this Pod. FRPC is no longer involved. Existing clients, passwords, masquerade configuration, and DNS records remain unchanged. The HTTPS gateway port 20443 does not apply. See [UDP gateway](../hysteria2-udp-gateway/README.md) for routing, verification and rollback.

Do not run the original Docker listener concurrently. The final replica count is one; initial migration stages the Deployment at zero while cert-manager issues its certificate. No PVC is necessary.

## Certificate lifecycle

`Certificate/hysteria2-tls` uses `ClusterIssuer/letsencrypt-cloudflare` and Cloudflare DNS01 to issue `*.yhzone.top`. The wildcard preserves existing client SNI values including services.yhzone.top, ali-sas.yhzone.top and debian.yhzone.top. A dedicated ECDSA key is generated and rotated by cert-manager, with renewal requested 30 days before expiry.

The resulting `hysteria2-tls` Secret is mounted as the entire `/certs` directory, **without subPath**, so Kubernetes projects renewed certificate files automatically. Hysteria reads certificate files on each new TLS handshake; no container restart or host certificate copy is required. See [Hysteria TLS documentation](https://v2.hysteria.network/docs/advanced/Full-Server-Config/#tls). Existing sessions are unaffected by certificate rotation.

The `hysteria2-config` Secret contains the existing password and masquerade configuration, with only listen address changed from `:443` to `:30443` and TLS paths changed to `/certs/tls.crt` and `/certs/tls.key`. It contains no embedded private key. `harbor-pull` is a project-scoped pull-only registry credential. Both are bootstrapped outside Git; preserve them for disaster recovery. Do not print client/server credentials or private keys in logs.

## Operations and rollback

```sh
kubectl --context yihao -n hysteria2 get pods,certificate
kubectl --context yihao -n hysteria2 logs deploy/hysteria2 --tail=20
```

A Ready process alone is not an end-to-end UDP health check. Verify authenticated Hysteria client connections with TLS verification and a proxied request. Do not add an HTTP/TCP probe to the UDP listener.

Original host config/certificate backups are private at `~/k8s/.bootstrap/hysteria2/source-before.tar.gz`. The old Docker container and image remain for rollback. After migration it is stopped, restart disabled, and Compose uses the `legacy-rollback` profile. To roll back, pause this Argo application's automated sync, scale the Kubernetes Deployment to zero, wait for UDP 30443 to be released, then restore/start Docker. Never let both listeners compete for the same host port.

## Migration validation (2026-09-24)

Argo CD Synced/Healthy, one Ready Pod; Docker stopped with restart disabled. Authenticated Hysteria clients with normal certificate verification successfully proxied HTTPS through 127.0.0.1:30443, ali-sas public IPv4 101.37.69.162:30443, and the first node global IPv6 address. The IPv6 test originated on the first node; independent external IPv6 ingress was not tested. The mounted certificate matches the cert-manager Secret and is issued by Let's Encrypt. Certificate expiry is 2026-12-23; cert-manager schedules renewal for 2026-11-23.

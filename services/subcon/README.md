# subcon

One local Helm chart and one Argo CD Application, deployed as a single Recreate replica on `yihao-pve-debian` (amd64). The original runtime image is stored in a private Harbor project and pinned by digest. Application dependencies were not upgraded.

- Public: https://subcon.yhzone.top:20443
- EasyTier: https://subcon.k8s.yhzone.top
- Retired: `subcon.d.yhzone.top:20443`; update existing clients/bookmarks. Browser localStorage is origin-specific and is not automatically copied to the new domain.
- Persistent claim: `subcon/subcon-data`, `1Gi`, StorageClass `yihao-local` (Retain). Data resides below `~/k8s/storage/pvc`, not in the container writable layer.

The PVC contains the original `conf` tree (profiles, API token, snippets, rules, cache and preferences) plus the two custom SSH/VMess schemas. The schemas retain their original read-only mount behavior. The image's remaining schemas are unchanged. API authentication and same-origin checks remain native to Subcon; no new Basic Auth layer is added. The original seven profiles and API token were verified through the API. Subcon normally clears its cache on startup; the original cache remains in the private backup and original host directory.

Original data mixes UID 1000 and root-owned files. The process keeps UID 0 and only adds DAC_OVERRIDE after dropping other capabilities, preserving the original file ownership while allowing configuration/cache writes.

## Data protection and validation

Migration date: 2026-09-24. Before cutover, writable source containers were stopped, their data copied into a private backup and PVC, and file hashes, modes and ownership compared before the new process started. Read-only FunASR models could be copied while the source ran. Original data directories/volumes and stopped Docker containers remain intact. The original image config ID is `sha256:86d58af5063e02b37ddf51579373aea069a8144149c826ac47d35420583a2258`.

Backup directory: `~/k8s/storage/backups/migration-20260924/subcon/`. It includes Docker runtime configuration, original Compose configuration, copied data, per-file SHA-256 manifests and a migration report. Access is restricted; contents may contain credentials. These are same-host backups, not protection against host/disk loss. Back up this directory and Kubernetes Secrets to a separate system for disaster recovery.

Registry credential `harbor-pull` and any `runtime-env`/`public-basic-auth` Secrets are provisioned outside Git. Preserve them alongside the PVC. Automatic Argo pruning is disabled; do not delete PVCs or backups when removing an Application.

All internal health endpoints and trusted TLS were checked. Public IPv4 through ali-sas and global IPv6 accessed from the first node were checked; independent external IPv6 ingress was not tested. Public DNS uses the existing controller and manual NodePublicIPv6 eligibility; cert-manager manages both HTTPS certificates.

## Rollback

The old Docker restart policy is `no`; Compose requires `--profile legacy-rollback`. Do not run old and new writable instances together. First pause Argo automated sync, scale this Deployment to zero, and wait for shutdown. If writes have occurred since migration, snapshot the current PVC and transfer current data back before starting Docker; blindly restoring the old snapshot would discard new changes. For Zhiyun, move the database and encryption key together and restore a valid ASR endpoint. Restore routing only after verifying the rollback instance. The original Caddy configuration is backed up at the migration root; restore only relevant site blocks to avoid undoing unrelated changes.

# funasr-nano

One local Helm chart and one Argo CD Application, deployed as a single Recreate replica on `yihao-pve-debian` (amd64). The original runtime image is stored in a private Harbor project and pinned by digest. Application dependencies were not upgraded.

- Public: https://funasr.yhzone.top:20443
- EasyTier: https://funasr.k8s.yhzone.top
- Retired: `funasr.d.yhzone.top:20443`; update existing clients/bookmarks. Browser localStorage is origin-specific and is not automatically copied to the new domain.
- Persistent claim: `funasr-nano/funasr-nano-data`, `4Gi`, StorageClass `yihao-local` (Retain). Data resides below `~/k8s/storage/pvc`, not in the container writable layer.

The two original GGUF model files (953550784 bytes total) were copied and SHA-256 verified against both backup and PVC. Models remain mounted read-only at `/models`. The CPU runtime was built for this node and remains pinned here. Existing runtime settings, including the API key and inference limits, are preserved in `runtime-env` outside Git.

Public realtime API: `wss://funasr.yhzone.top:20443/v1/realtime`. The existing Bearer API key is unchanged. No Basic Auth is added over the native API authentication. Public WebSocket authentication and a complete CPU inference using the migrated model files were verified. Shared process namespace replaces the old Docker init role for subprocess cleanup.

## Data protection and validation

Migration date: 2026-09-24. Before cutover, writable source containers were stopped, their data copied into a private backup and PVC, and file hashes, modes and ownership compared before the new process started. Read-only FunASR models could be copied while the source ran. Original data directories/volumes and stopped Docker containers remain intact. The original image config ID is `sha256:8063c09c51102c69d1d2d3e5c18f308a9f92b59393a4254804c68c1829fcf90b`.

Backup directory: `~/k8s/storage/backups/migration-20260924/funasr-nano/`. It includes Docker runtime configuration, original Compose configuration, copied data, per-file SHA-256 manifests and a migration report. Access is restricted; contents may contain credentials. These are same-host backups, not protection against host/disk loss. Back up this directory and Kubernetes Secrets to a separate system for disaster recovery.

Registry credential `harbor-pull` and any `runtime-env`/`public-basic-auth` Secrets are provisioned outside Git. Preserve them alongside the PVC. Automatic Argo pruning is disabled; do not delete PVCs or backups when removing an Application.

All internal health endpoints and trusted TLS were checked. Public IPv4 through ali-sas and global IPv6 accessed from the first node were checked; independent external IPv6 ingress was not tested. Public DNS uses the existing controller and manual NodePublicIPv6 eligibility; cert-manager manages both HTTPS certificates.

## Rollback

The old Docker restart policy is `no`; Compose requires `--profile legacy-rollback`. Do not run old and new writable instances together. First pause Argo automated sync, scale this Deployment to zero, and wait for shutdown. If writes have occurred since migration, snapshot the current PVC and transfer current data back before starting Docker; blindly restoring the old snapshot would discard new changes. For Zhiyun, move the database and encryption key together and restore a valid ASR endpoint. Restore routing only after verifying the rollback instance. The original Caddy configuration is backed up at the migration root; restore only relevant site blocks to avoid undoing unrelated changes.

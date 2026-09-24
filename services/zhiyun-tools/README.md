# zhiyun-tools

One local Helm chart and one Argo CD Application, deployed as a single Recreate replica on `yihao-pve-debian` (amd64). The original runtime image is stored in a private Harbor project and pinned by digest. Application dependencies were not upgraded.

- Public: https://zhiyun.yhzone.top:20443
- EasyTier: https://zhiyun.k8s.yhzone.top
- Retired: `zhiyun.d.yhzone.top:20443`; update existing clients/bookmarks. Browser localStorage is origin-specific and is not automatically copied to the new domain.
- Persistent claim: `zhiyun-tools/zhiyun-tools-data`, `10Gi`, StorageClass `yihao-local` (Retain). Data resides below `~/k8s/storage/pvc`, not in the container writable layer.

The PVC preserves `zhiyun.db`, `settings.json` and `credentials.key` together. The SQLite WAL was included in the migration process and allowed to checkpoint during graceful shutdown; final offline copies passed `PRAGMA integrity_check`. All 20 original job rows and 9466 transcript rows were compared after startup and preserved, including their full contents. The encryption key is byte-identical and the application successfully decrypted its credentials and connected.

The only deliberate saved-settings change is `asr_api_url`, now `ws://funasr-nano-internal.funasr-nano.svc.cluster.local/v1/realtime`, replacing the retired public hostname. Existing encrypted account/password and ASR key values remain unchanged. Connectivity to FunASR was verified from this Pod.

The public Ingress uses the original Zhiyun Caddy Basic Auth credentials stored in `public-basic-auth`; internal access has no additional Basic Auth. No active or queued recognition jobs existed before stopping the original container. The application normally marks active jobs interrupted on restart; stored transcript history remains persistent. Shared process namespace provides subprocess reaping.

## Data protection and validation

Migration date: 2026-09-24. Before cutover, writable source containers were stopped, their data copied into a private backup and PVC, and file hashes, modes and ownership compared before the new process started. Read-only FunASR models could be copied while the source ran. Original data directories/volumes and stopped Docker containers remain intact. The original image config ID is `sha256:a26decfc5e83f6f4cb92e3dec714b7795b52cc1dc0402bf67abda3b9f2326b99`.

Backup directory: `~/k8s/storage/backups/migration-20260924/zhiyun-tools/`. It includes Docker runtime configuration, original Compose configuration, copied data, per-file SHA-256 manifests and a migration report. Access is restricted; contents may contain credentials. These are same-host backups, not protection against host/disk loss. Back up this directory and Kubernetes Secrets to a separate system for disaster recovery.

Registry credential `harbor-pull` and any `runtime-env`/`public-basic-auth` Secrets are provisioned outside Git. Preserve them alongside the PVC. Automatic Argo pruning is disabled; do not delete PVCs or backups when removing an Application.

All internal health endpoints and trusted TLS were checked. Public IPv4 through ali-sas and global IPv6 accessed from the first node were checked; independent external IPv6 ingress was not tested. Public DNS uses the existing controller and manual NodePublicIPv6 eligibility; cert-manager manages both HTTPS certificates.

## Rollback

The old Docker restart policy is `no`; Compose requires `--profile legacy-rollback`. Do not run old and new writable instances together. First pause Argo automated sync, scale this Deployment to zero, and wait for shutdown. If writes have occurred since migration, snapshot the current PVC and transfer current data back before starting Docker; blindly restoring the old snapshot would discard new changes. For Zhiyun, move the database and encryption key together and restore a valid ASR endpoint. Restore routing only after verifying the rollback instance. The original Caddy configuration is backed up at the migration root; restore only relevant site blocks to avoid undoing unrelated changes.

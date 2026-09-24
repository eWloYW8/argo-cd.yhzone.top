# ascend-compiler-explorer

One local Helm chart and one Argo CD Application, deployed as a single Recreate replica on `yihao-pve-debian` (amd64). The original runtime image is stored in a private Harbor project and pinned by digest. Application dependencies were not upgraded.

- Public: https://ascendc.yhzone.top:20443
- EasyTier: https://ascendc.k8s.yhzone.top
- Retired: `ascendc.d.yhzone.top:20443`; update existing clients/bookmarks. Browser localStorage is origin-specific and is not automatically copied to the new domain.
- Persistent claim: `ascend-compiler-explorer/ascend-compiler-explorer-data`, `10Gi`, StorageClass `yihao-local` (Retain). Data resides below `~/k8s/storage/pvc`, not in the container writable layer.

The original CANN 9.0.1 / Ascend 910B runtime image is preserved without rebuilding its toolchain or updating dependencies. Existing writable-layer paths `/opt/compiler-explorer/lib/storage/data` and `/opt/compiler-explorer/out/compiler-cache` now use PVC subdirectories. The original shell history is separately preserved in the private backup, not published or mounted into the service.

Both `ascend910b-aiv` and `ascend910b-aic` are available. The existing vector-add example compiled successfully via the API and returned 1055 assembly lines. CPU execution of Ascend code remains disabled according to the original application configuration. Shared process namespace allows the Pod sandbox to act as PID 1 for compiler subprocess cleanup.

## Data protection and validation

Migration date: 2026-09-24. Before cutover, writable source containers were stopped, their data copied into a private backup and PVC, and file hashes, modes and ownership compared before the new process started. Read-only FunASR models could be copied while the source ran. Original data directories/volumes and stopped Docker containers remain intact. The original image config ID is `sha256:a92158b47453a1771a149b588e5ef5546c18d859ed72626e094a432fc11d1a25`.

Backup directory: `~/k8s/storage/backups/migration-20260924/ascend-compiler-explorer/`. It includes Docker runtime configuration, original Compose configuration, copied data, per-file SHA-256 manifests and a migration report. Access is restricted; contents may contain credentials. These are same-host backups, not protection against host/disk loss. Back up this directory and Kubernetes Secrets to a separate system for disaster recovery.

Registry credential `harbor-pull` and any `runtime-env`/`public-basic-auth` Secrets are provisioned outside Git. Preserve them alongside the PVC. Automatic Argo pruning is disabled; do not delete PVCs or backups when removing an Application.

All internal health endpoints and trusted TLS were checked. Public IPv4 through ali-sas and global IPv6 accessed from the first node were checked; independent external IPv6 ingress was not tested. Public DNS uses the existing controller and manual NodePublicIPv6 eligibility; cert-manager manages both HTTPS certificates.

## Rollback

The old Docker restart policy is `no`; Compose requires `--profile legacy-rollback`. Do not run old and new writable instances together. First pause Argo automated sync, scale this Deployment to zero, and wait for shutdown. If writes have occurred since migration, snapshot the current PVC and transfer current data back before starting Docker; blindly restoring the old snapshot would discard new changes. For Zhiyun, move the database and encryption key together and restore a valid ASR endpoint. Restore routing only after verifying the rollback instance. The original Caddy configuration is backed up at the migration root; restore only relevant site blocks to avoid undoing unrelated changes.

# ZJU-Autosign

A continuous background worker migrated from `~/docker/ZJU-Autosign`. This service has no HTTP interface, Service, Ingress, public domain, or persistent files. It polls the existing upstream every four seconds. Existing radar rollcall behavior and manual number-rollcall notifications are preserved.

The local Helm chart deploys one replica on `yihao-pve-debian` with Recreate strategy. Never run the legacy Docker container concurrently. The original runtime image, including uncommitted local source changes relative to `765f68f3c9d8e9eee29bfa13c8054c90ed1f1f8c`, is stored in the private Harbor project `zju-autosign` and pinned by digest. It is amd64 only. Core files were compared with the live container before migration. Application code and dependency versions are unchanged.

## Credentials and state

The `autosign-env` Secret contains the five existing runtime environment values: ZJU_USERNAME, ZJU_PASSWORD, ENABLE_DINGTALK, DINGTALK_WEBHOOK and DINGTALK_SECRET. Credentials are bootstrapped outside Git. `harbor-pull` contains a project-scoped pull-only robot credential. Back up both Secrets separately from Git; source archives containing `.env` are private backups, not repository artifacts.

There are no database files or volumes to migrate, so no PVC is allocated. In-memory number-rollcall notification deduplication resets on restart. Normal startup/shutdown notifications remain enabled according to the existing configuration. Future persistent state should use `yihao-local` under the configured `~/k8s/storage` root.

The worker runs without root, with a read-only root filesystem and a small ephemeral `/tmp`. No artificial HTTP health endpoint is added: Kubernetes observes process exits, while successful upstream polling must be checked in application logs. A Running/Ready Pod alone does not prove upstream authentication works. The existing worker catches upstream polling errors and retries; repeated failures need operator attention.

## Operations

```sh
kubectl --context yihao -n zju-autosign get pods
kubectl --context yihao -n zju-autosign logs deploy/zju-autosign --tail=30
```

Logs can contain account/course details and notification errors; do not publish them without review. After changing `autosign-env`, restart the Deployment explicitly so the process receives the new environment.

Source and environment backup: `~/k8s/.bootstrap/zju-autosign/source-before.tar.gz` (private, outside Git). The stopped original container and image are retained; Compose uses the `legacy-rollback` profile and restart policy `no` after cutover.

For rollback, first disable automated sync for the `zju-autosign` Argo CD Application, scale its Deployment to zero and wait for the Pod to terminate, then restore the original Compose configuration from the backup and start the legacy container. Never overlap the two workers.

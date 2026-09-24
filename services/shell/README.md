# Shell static files

Public URL: **https://shell.yhzone.top:20443**. Existing paths and public access are preserved; directory browsing is disabled. Files are served as static content, never executed.

Edit files directly on `yihao-pve-debian` as `yihao`:

```sh
cd ~/k8s/storage/shell
cp ~/example.sh ./example.sh
# Available immediately at https://shell.yhzone.top:20443/example.sh
rm ./example.sh
```

Changes require no Git commit, Pod restart or redeployment. For large files, upload outside this directory first, then move the completed file into it on the same filesystem to avoid partial downloads.

A statically bound `yihao-local` PV/PVC points to `/home/yihao/k8s/storage/shell`; the PV uses `Retain`. Its declared 5 GiB capacity is scheduling metadata, not a filesystem quota. The Deployment is pinned to this node. Nginx runs as UID/GID 1000 with the files mounted read-only; original file permissions are retained. Config changes are managed by this local Helm chart and Argo CD.

The public Ingress uses `traefik-public`; cert-manager renews its Let's Encrypt certificate through Cloudflare DNS-01. The public-network controller and ExternalDNS manage public IPv4/IPv6 records and the port 20443 SNI route.

Migration retained the original directory `~/docker/caddy/shell` and a checksum-verified backup in `~/k8s/storage/backups/shell-migration-20260924`. These are snapshots; update only the new live directory. Back up that directory regularly. Deleting the Application does not constitute a data backup; avoid deleting the host files or repurposing its retained PV.

# Resource ownership audit — 2026-09-24

Audit scope: live resources in context `yihao`, compared with all Argo CD Application resource inventories and rendered service manifests. No missing business Deployment, StatefulSet, DaemonSet, Service, Ingress, standalone PVC or NodePublicIPv6 declaration was found.

## Gaps addressed

- Added 20 explicit Namespace manifests to the corresponding service directories. `local-path-storage` was already declared. `external-dns-public` shares the namespace owned by `external-dns`; `hysteria2-udp-gateway` shares the namespace owned by `public-network`.
- Retained the currently empty `platform-certificates` namespace under cert-manager. Namespace creation was previously implicit (`CreateNamespace=true`) or manual. Explicit manifests now give them a single GitOps owner. Newly declared namespaces use `Prune=false,Delete=false` to prevent accidental namespace-wide data removal.
- Included the existing root `Application/argocd/yihao` manifest in `clusters/yihao/kustomization.yaml`. It still needs initial bootstrap on a new cluster, then manages its own declaration.
- Recorded 29 externally provisioned Secret dependencies, including their required key names, in [the bootstrap inventory](../bootstrap/secret-inventory.yaml). This inventory is documentation, not a Secret manifest and not a credential backup. Actual values remain outside Git. Do not create empty placeholder Secrets: they can overwrite working credentials.

## Resources deliberately owned by other controllers

| Resources | Source of truth / owner |
| --- | --- |
| Pods, ReplicaSets, ControllerRevisions, Jobs from CronJobs | Deployment / StatefulSet / DaemonSet / CronJob manifests |
| Service Endpoints / EndpointSlices | Kubernetes service controllers |
| Ingress-generated Certificates, CertificateRequests, Orders, Challenges, TLS Secrets | Ingress TLS declarations, cert-manager and ClusterIssuer |
| Public DNSEndpoints and `public-network/public-edge-routes` | public-network controller, public Ingress and manual NodePublicIPv6 declarations |
| Dynamically provisioned PVs | Declared PVCs and yihao-local provisioner; preserve actual data separately |
| Harbor database/Redis generated PVCs | StatefulSet volumeClaimTemplates; preserve original bound volumes |
| Default ServiceAccounts, kube-root-ca.crt, leases, events and metrics | Kubernetes controllers / runtime |
| Nodes and K3s system resources (CoreDNS, metrics-server, default RBAC, API priority rules, RuntimeClasses, K3s CRDs) | K3s bootstrap and packaged components; host configuration is under bootstrap/ |
| Argo CD initial admin/Redis secrets, webhook CA, ACME account | Component initialization and certificate controllers |

Do not export live objects wholesale into Git: runtime status, generated names and credentials are not desired configuration. Avoid assigning Argo CD ownership to controller outputs.

## Secrets and disaster recovery

The 29 external Secrets include GitHub repository access, Cloudflare credentials, Harbor bootstrap/signing credentials, image pull credentials, Basic Auth, Hysteria2 configuration and application/database environment values. Workloads already reference them, but their values cannot be reconstructed from Git.

Existing import/seed helpers are in the relevant service directories, including cert-manager, external-dns, Harbor and public-network. Other imported application credentials require a protected backup or the original source. Restoring an existing database requires its original passwords/signing material; do not blindly regenerate them.

A future encrypted-secret or external-secret backend could make secret restoration declarative, but none is currently deployed. This audit does not claim those 29 Secrets are reconciled by Argo CD. Keep credential backups, PV/application data and K3s recovery material outside the repository.

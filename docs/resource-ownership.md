# Resource ownership audit — 2026-09-24

Audit scope: live resources in context `yihao`, compared with all Argo CD Application resource inventories and rendered service manifests. No missing business Deployment, StatefulSet, DaemonSet, Service, Ingress, standalone PVC or NodePublicIPv6 declaration was found.

## Gaps addressed

- Added 20 explicit Namespace manifests to the corresponding service directories. `local-path-storage` was already declared. `external-dns-public` shares the namespace owned by `external-dns`; `hysteria2-udp-gateway` shares the namespace owned by `public-network`.
- Retained the currently empty `platform-certificates` namespace under cert-manager. Namespace creation was previously implicit (`CreateNamespace=true`) or manual. Explicit manifests now give them a single GitOps owner. Newly declared namespaces use `Prune=false,Delete=false` to prevent accidental namespace-wide data removal.
- Included the existing root `Application/argocd/yihao` manifest in `clusters/yihao/kustomization.yaml`. It still needs initial bootstrap on a new cluster, then manages its own declaration.
- Initially identified 29 external Secret dependencies. Subsequently adopted 28 into the private Secret repository through Application `yihao-secrets`. The old configuration-repository access credential is unnecessary now that the configuration repository is public. The private repository access Secret remains bootstrap-only. See [the dependency inventory](../bootstrap/secret-inventory.yaml); it contains no values.

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

The public configuration repository contains no credential values. The private repository `eWloYW8/argo-cd-secrets.yhzone.top` stores 28 user-authorized unencrypted Secret manifests, grouped by namespace. Base64 `data` preserves bytes and supports Server-Side Apply; it is not encryption.

Application `yihao-secrets` uses a dedicated project permitting only Secrets in the required namespaces. Both automatic pruning and deletion of individual Secrets are disabled. Values, names and namespaces were preserved during adoption. Changing credentials through Git may require restarting their consumers.

The private repository is read using a dedicated read-only GitHub deploy key. Its private key is bootstrap material outside both repositories, stored locally in `~/k8s/.bootstrap/repo-split/secrets-deploy-key` and in `argocd/yihao-secrets-git-repository`. Restore this access Secret before reconciling the private Application on a new cluster; alternatively register a new read-only deploy key. The public repository can be cloned without credentials.

Controller-generated certificates, ACME state and service-account tokens remain outside this private repository. Persistent application data and K3s recovery material still require separate protected backups. Keeping a private plaintext Git repository does not protect against access by collaborators or compromised clone copies.

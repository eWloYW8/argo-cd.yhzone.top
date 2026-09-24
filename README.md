# yihao GitOps

K3s / EasyTier 私有集群，默认 context 为 `yihao`。首节点 `yihao-pve-debian`，API 为 `https://10.1.2.4:6443`。

## 目录约定

```text
services/
  argocd/                  # Argo CD 自管理与项目权限
  cert-manager/            # Helm + Cloudflare ACME 签发器
  external-dns/            # Helm + Cloudflare DNS 自动管理
  harbor/                  # Helm + PostgreSQL + 缓存初始化任务
  headlamp/                # Helm + 登录 RBAC
  traefik/                 # Helm + 标准 Ingress 内网 HTTPS 入口
  local-path-provisioner/  # 本地存储
clusters/yihao/             # 根 Application、ApplicationSet
bootstrap/                 # K3s、LXC、宿主机引导
docs/                      # 访问、恢复等运维说明
```

每个服务一个目录、一个 Application：

```text
services/harbor/
  app.yaml                 # Application 名称、namespace、差异忽略规则
  kustomization.yaml       # 服务入口：Helm Chart + 补充资源
  values/harbor-1.19.2.yaml # 对应版本的完整默认值及本集群修改
  resources/               # 数据库、PostSync 缓存初始化等
  scripts/                 # 该服务的引导工具
```

结构借鉴 `argo-cd.clusters.zjusct.io`。ApplicationSet 自动发现 `services/*/app.yaml`，无需为每个服务手写 Application。资源名称与 namespace 不强制随文件夹重命名，以保留存储与访问地址。纯清单服务使用 Kustomize；Argo CD 沿用固定版本官方清单，避免本次目录整理同时更换安装来源。

`charts/` 是 Kustomize 下载缓存，不提交 Git。Helm Chart 版本在各服务 `kustomization.yaml` 中固定，values 文件名包含对应版本。真实凭据通过 Secret 引导，不写入 values 或 Git。

## 修改与验证

```sh
kubectl kustomize --enable-helm services/harbor
kubectl kustomize clusters/yihao
```

需要本机安装 Helm。渲染输出可能包含 Secret，不要提交或公开。提交遵循 Conventional Commits，例如 `feat(harbor): ...`、`fix(cert-manager): ...`。

新增服务时，增加服务目录、`app.yaml` 与 `kustomization.yaml` 后提交即可。ApplicationSet 采用 create-update，且自动 prune 关闭；移除服务需要显式检查并处理 Application 与资源，避免误删持久化数据。

## 访问

- https://headlamp.k8s.yhzone.top
- https://argo-cd.k8s.yhzone.top
- https://harbor.k8s.yhzone.top

DNS 指向 EasyTier `10.1.2.4`，仅内网 443，公网入口尚未配置。登录和缓存用法见 [访问说明](docs/access.md)。

## 引导与恢复

`bootstrap/k3s/config.yaml` 仅用于首节点；K3s 由宿主机 systemd 管理。先完成 PVE sysctl、EasyTier 和 K3s 安装，再运行 `bootstrap/resume.sh`。已有集群直接使用 `yihao` context。

私有仓库连接：`services/argocd/scripts/connect-github.sh`，只读 token 交互录入。它创建项目并应用 `clusters/yihao/application.yaml`。凭据初始化与恢复要求见访问说明。

PVC 数据位于 `~/k8s/storage/pvc`，etcd 快照位于 `~/k8s/storage/etcd-snapshots`。当前与系统盘共用文件系统；同盘快照不是异机备份。恢复需要数据库/镜像数据、Secret 和 K3s server token。

新增节点需固定 EasyTier IP，检查与 Pod `10.42.0.0/16`、Service `10.43.0.0/16` 的网段冲突；不要复制首节点 cluster-init 配置。本地持久卷只放在首节点。

LXC 的 `/dev/kmsg` 使用 console 兼容链接，内核 OOM 观测存在限制；NetworkManager 排除 CNI 接口的配置位于 `bootstrap/k3s/`。

DNS 自动管理与服务注解用法见 [ExternalDNS](services/external-dns/README.md)。

新增 HTTP 服务使用各自目录中的 Ingress，自动完成路由、证书及 DNS 配置，见 [入口说明](services/traefik/README.md)。

普通服务默认采用 [Harbor 镜像前缀](services/harbor/README.md)，通过共享 Kustomize component 管理；基础启动组件保留直连上游。Argo CD 访问地址为 `https://argo-cd.k8s.yhzone.top`。

第二个节点 `ali-sas`（EasyTier `10.1.2.2`）作为 worker 加入，部署与资源限制见 [节点说明](bootstrap/nodes/ali-sas/README.md)。

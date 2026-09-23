# yihao Kubernetes infrastructure

独立 K3s 集群，通过 EasyTier 连接节点。现有 zjusct 集群不属于本仓库。

- 首节点：`yihao-pve-debian`，EasyTier `10.1.2.4` / `tun0`，LXC。
- API：`https://10.1.2.4:6443`。
- Pod CIDR：`10.42.0.0/16`；Service CIDR：`10.43.0.0/16`。
- 默认 PVC：`yihao-local`，数据目录 `/home/yihao/k8s/storage/pvc`。
- etcd 快照：`/home/yihao/k8s/storage/etcd-snapshots`。同盘快照不是异机备份。
- 版本在 `bootstrap/versions.env` 中固定。

## 使用

```sh
kubectl --context yihao get nodes -o wide
kubectl --context yihao -n argocd port-forward svc/argocd-server 8080:443
```

Argo CD 访问 `https://localhost:8080`，初始账号 `admin`；密码通过以下命令在自己的终端读取，勿提交 Git：

```sh
kubectl --context yihao -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

## 存储

本地卷绑定首节点，节点离线时不会自动迁移。Retain 防止删除 PVC 后立即清除数据；卷回收需要人工处理。请求容量不等于磁盘配额。当前数据与系统位于同一文件系统，需监控剩余空间并另建异机备份。

## 引导与 GitOps

`bootstrap/k3s/config.yaml` 仅供首节点使用；K3s 是宿主机服务，由 systemd 管理。Argo CD 安装配置位于 `bootstrap/argocd`。GitOps 根路径为 `clusters/yihao`。

GitHub 地址确定并推送后再创建根 Application。私有仓库凭据只写 Kubernetes Secret，不提交本仓库。初期不启用自动 prune。

Headlamp、Harbor 代理缓存、cert-manager 和内网 Caddy 已纳入 GitOps。访问方式、登录命令及网络边界见 [服务访问说明](docs/access.md)。异机备份与公网入口尚未配置。

## 新节点

先安装 EasyTier，确保固定 IP、API TCP 6443、节点间 VXLAN UDP 8472 和 kubelet TCP 10250 可达。新节点单独配置 node-ip、node-name、flannel-iface；token 从首节点受保护的 `/var/lib/rancher/k3s/server/agent-token` 安全传递。不得复制首节点的 cluster-init 配置。新节点加入前检查网段冲突，加入后验证跨节点 DNS、Pod 通信、MTU 与镜像架构。

## LXC 兼容配置

`/etc/tmpfiles.d/yihao-k3s-kmsg.conf` 在 `/dev/kmsg` 缺失时链接到 `/dev/console`，让 kubelet 启动。这不是实际内核日志设备，因此内核 OOM 事件观测存在限制。未修改 PVE 宿主机配置。

## 初始化与恢复

2026-09-23：首节点 Ready；Argo CD 和本地存储 provisioner 已安装；集群 DNS、PVC 挂载写入、Pod 重建后的数据读取均已验证。PVE 宿主机所需 sysctl 已生效。`yihao` 为默认 context。

1. 重建前在 PVE 宿主机审阅并应用 `bootstrap/pve-sysctl.conf` 中的三个参数，持久化到 `/etc/sysctl.d/`。这些参数影响宿主机及其他容器。
2. 安装固定版本 K3s 并恢复管理员 kubeconfig 后，本机执行 `./bootstrap/resume.sh` 引导节点、存储 provisioner 和 Argo CD。
3. 本机执行 `gh auth login -h github.com` 登录 GitHub。
4. 执行 `./bootstrap/connect-github.sh` 推送 main、交互录入只读 token 并连接 GitOps。推送使用本机 gh 登录；Argo CD token 仅写入集群 Secret，不进入 Git。

初始 etcd 快照已创建在 `storage/etcd-snapshots`。恢复加密数据还需安全备份 `/var/lib/rancher/k3s/server/token`，不可提交 Git。快照与 PVC 当前都在本机系统盘，尚无异机备份。

私有仓库：https://github.com/eWloYW8/argo-cd.yhzone.top 。根 Application 部署 `clusters/yihao`，其中含独立的 Argo CD 自管理 Application。默认存储只允许首节点，新增节点不会自动承载持久卷。

Argo CD 与本机 git origin 均使用 HTTPS。轮换只读 token：运行 `python3 bootstrap/configure-repository.py`。

NetworkManager 通过 `bootstrap/k3s/networkmanager.conf` 排除 CNI 与 Flannel 接口，防止自动 DHCP 接管并拆离 Pod veth。配置安装在 `/etc/NetworkManager/conf.d/90-yihao-k3s.conf`。

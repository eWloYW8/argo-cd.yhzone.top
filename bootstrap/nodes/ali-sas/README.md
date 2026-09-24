# ali-sas worker

- SSH: `ssh ali-sas`，系统主机名 `yihao-ali-sas`，Kubernetes 节点名 `ali-sas`。
- Debian 13 / amd64，2 CPU，约 1.64 GiB RAM，EasyTier `tun0` 地址 `10.1.2.2/24`。
- K3s agent `v1.36.4+k3s1`，连接 `https://10.1.2.4:6443`；systemd 自启并等待 EasyTier 地址就绪。
- Flannel VXLAN 经 tun0，Pod CIDR 由集群分配，当前 `10.42.1.0/24`，隧道 MTU 1310。
- 本节点只承担 worker 职责，不增加 etcd/control-plane 副本。默认 kubeconfig 仍为 yihao。

## 资源与存储

已有 frps、Docker、EasyTier 和云平台代理等服务，加入后空余内存约 180 MiB。为现有系统服务预留 1280 MiB、K3s/kubelet 预留 256 MiB，可调度内存约 147 MiB；CPU 预留合计 300m。仅适合轻量工作负载，预留值是调度预算，不能代替应用内存 requests/limits。扩大负载前先检查实际内存余量并调整配置。

`yihao-local` 仍只在首节点创建持久卷，本节点不提供默认本地持久化存储；已有数据和入口未迁移。

## 主机配置

- 本目录 `config.yaml` → `/etc/rancher/k3s/config.yaml`（root:root 0600）。
- `easytier.conf` → `/etc/systemd/system/k3s-agent.service.d/easytier.conf`。
- Token → `/etc/rancher/k3s/agent-token`（root:root 0600），仅通过 SSH stdin 传入，不进入仓库。
- 注册标签 `node.yhzone.top/role=worker`。`node-role.kubernetes.io/worker=true` 由管理员通过 kubectl 添加，不能作为 kubelet 注册参数。
- kubelet 使用默认监听以兼容 K3s agent tunnel；systemd 启动前限制 eth0 上的 TCP 10250（IPv4/IPv6），UDP 8472 只允许从 tun0 进入。

## 安装与恢复

使用与首节点相同的 K3s 二进制，传输后校验 SHA256。安装前复制配置、Secret token 和 systemd drop-in，然后运行官方 K3s 安装脚本，设置 `INSTALL_K3S_SKIP_DOWNLOAD=true INSTALL_K3S_EXEC=agent`。启用并启动 `k3s-agent.service`。

该主机直连 Docker Hub 的基础 pause 镜像拉取超时，因此从同架构首节点导出并预置：

```sh
sudo k3s ctr -n k8s.io images export --platform linux/amd64 /tmp/pause.tar \
  docker.io/rancher/mirrored-pause:3.10.2
```

将文件经 SSH 复制到新节点 `/var/lib/rancher/k3s/agent/images/pause.tar`（0644）。K3s 启动时自动导入。保留此文件，避免 Pod sandbox 启动依赖 Harbor 或 Docker Hub 在线可用；升级 K3s 时检查所需 pause 版本并同步更新。业务镜像使用 `harbor.k8s.yhzone.top` 前缀。

修改配置后执行 `sudo systemctl daemon-reload && sudo systemctl restart k3s-agent`。更换机器重建同名节点前应先处理旧节点及 `/etc/rancher/node/password` 身份，不要直接覆盖已有 K3s 安装。

## 已验证

2026-09-24：两个节点 Ready；新节点成功从 Harbor 拉取镜像；Pod 双向跨节点 HTTP 与 64 KiB 传输、集群 DNS、跨节点 Harbor ClusterIP 服务访问、kubectl exec 均通过。临时测试 namespace 与调度 taint 已清理。

# Hysteria2 UDP gateway

Argo CD 管理的独立 Traefik UDP 网关，固定运行在 `ali-sas`，接管原 FRPS UDP 30443。镜像与现有公网网关一致，使用已缓存的上游 `docker.io/traefik:v3.7.13`，避免网络基础设施启动依赖 Harbor。无 Kubernetes API 凭据或额外 RBAC。

## 流量路径

`公网 IPv4:30443/UDP → ali-sas Traefik UDP → hysteria2-udp.hysteria2.svc.cluster.local:30443 → 首节点 Hysteria2`

后端为标准 Kubernetes ClusterIP Service，由标签选择实际 Hysteria2 Pod；当前 Pod 使用 hostNetwork，EndpointSlice 指向首节点 EasyTier 地址。UDP 路由使用本服务的 ConfigMap，由 Helm 声明。Traefik 仅中转 UDP，TLS、认证和证书轮换仍由 Hysteria2 / cert-manager 处理。公网 IPv6 仍直达首节点 UDP 30443，客户端域名、端口、密码和 SNI 均不改。

单副本 Recreate，监听 IPv4 `0.0.0.0:30443/udp`，UDP 会话超时 120 秒。健康检查 `127.0.0.1:18082/ping` 只表示网关进程就绪，不代表后端认证成功。网关重启/升级可能中断现有 UDP 会话，客户端需重连；这不是高可用部署。

使用独立 Deployment 是因为首节点 Hysteria2 已绑定相同 UDP 端口，不能把相同监听直接添加到跨节点的公网 Traefik DaemonSet。

## 验证与切换

先在临时 UDP 31443 验证 EasyTier 和公网 IPv4 的真实 Hysteria2 客户端认证、系统 CA 证书校验、代理 HTTPS 请求，再删除 FRPC 的 hysteria 条目并切换到正式 UDP 30443。临时端口不保留。FRPC 历史 EasyTier UDP 22020 条目未在本次清理。

FRPC 配置备份在 `~/k8s/storage/backups/hysteria2-udp-20260924/frpc.toml.before`，含敏感凭据，不进入 Git。

## 回退

先将本服务 replicas 在 Git 中改为 0，等待 Pod 完全退出并确认 UDP 30443 释放，再恢复 FRPC 的 hysteria UDP 条目并重启 FRPC。恢复时保留当前其他条目，不覆盖后续变更。不能同时启动 FRPS 与此网关占用 ali-sas 的相同 UDP 端口。后端 Hysteria2 与证书无需回退。

切换后正式 `101.37.69.162:30443` 和首节点 IPv6 `:30443` 均通过认证 TLS 与代理 HTTPS 实测；IPv6 测试由首节点发起，未声称从独立外部 IPv6 网络验证。ali-sas UDP 30443 的监听进程为 Kubernetes Traefik，31443 已释放。

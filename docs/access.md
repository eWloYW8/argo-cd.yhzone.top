# 服务访问与网络边界

| 服务 | 当前内网地址 |
| --- | --- |
| Headlamp | https://headlamp.k8s.yhzone.top |
| Argo CD | https://argo-cd.k8s.yhzone.top |
| Harbor | https://harbor.k8s.yhzone.top |

ExternalDNS 从各服务 Ingress 管理 Cloudflare DNS-only A 记录，三个服务域名均指向 `10.1.2.4`；原有 `*.k8s.yhzone.top` 泛解析保留。Traefik 以 hostNetwork 运行，仅监听首节点 EasyTier 地址 `10.1.2.4:443`，根据标准 Ingress 转发到集群 Service。需要加入 EasyTier 或有到该地址的路由才能访问。公网 20443 由独立 SNI/Traefik 入口接管，原 Docker Caddy 与 FRP 移至本机 21443，由 SNI 层转发，原服务外部地址保持 20443。

cert-manager 根据 Ingress 注解自动创建每服务的 Certificate，使用 Let's Encrypt ACME 和 Cloudflare DNS-01。TLS Secret 保存在各服务 namespace，Traefik 自动加载更新，无需手写 Caddyfile 或定时重载脚本。DNS 自检使用 DoH。新增服务见 [Ingress 配置](../services/traefik/README.md)。

## 登录

Headlamp 使用个人专用 ServiceAccount 的短期令牌；该账号为集群管理员，勿分享：

```sh
kubectl --context yihao -n headlamp create token yihao-admin --duration=1h
```

Headlamp 服务自身的 ServiceAccount 未授予 cluster-admin；用户需要主动登录。

Argo CD 账号 `admin`，初始密码（修改后应删除初始密码 Secret）：

```sh
kubectl --context yihao -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
```

Harbor 账号 `admin`，初始化密码：

```sh
kubectl --context yihao -n harbor get secret harbor-bootstrap -o jsonpath='{.data.HARBOR_ADMIN_PASSWORD}' | base64 -d
```

## 镜像缓存

普通服务采用 `harbor.k8s.yhzone.top/<上游 registry>/<镜像>` 前缀，Argo CD 和 Headlamp 已接入。公共上游缓存允许匿名拉取，例如：

```sh
docker pull harbor.k8s.yhzone.top/docker.io/library/busybox:1.37.0
```

管理账号为 admin；需要管理或访问原私有 dockerhub 项目时执行 `docker login harbor.k8s.yhzone.top`。原私有项目及镜像保留，公网使用 `harbor.yhzone.top:20443`。缓存项目配额总和为 30 GiB，按上游分配；配置及使用方式见 [Harbor 说明](../services/harbor/README.md)。Kustomize 为普通服务统一添加前缀，节点全局镜像源未改写，启动基础组件仍直连上游。

registry PVC 仍为 30 GiB、PostgreSQL 5 GiB、Redis 1 GiB、任务日志 1 GiB，均位于 `~/k8s/storage/pvc`。本地 PVC 大小不是文件系统硬配额。缓存需要保留策略/垃圾回收，不保证自动 LRU 淘汰。Trivy 暂未启用。

## 公网入口

目前公开 Harbor：`https://harbor.yhzone.top:20443`。A 为 ali-sas 公网 IPv4 `101.37.69.162`，AAAA 由手工 NodePublicIPv6 资源及实际服务后端节点决定。其余内网域名不在公网入口发布，公网 SNI 层拒绝 `*.k8s.yhzone.top`。

Harbor externalURL 和认证 realm 为 `https://harbor.yhzone.top:20443`；内网镜像前缀仍为 `harbor.k8s.yhzone.top`。两个节点已验证此组合的镜像拉取。公网客户端使用：

```sh
docker login harbor.yhzone.top:20443
docker pull harbor.yhzone.top:20443/docker.io/library/busybox:1.37.0
```

公共缓存项目支持匿名拉取；私有项目需登录。新增公开服务、IPv6 手工登记/撤销及旧服务转发说明见 [公网入口](../services/public-network/README.md)。

## 凭据恢复

Cloudflare 凭据从现有 Caddy compose 环境读取，用 `python3 services/cert-manager/scripts/import-cloudflare.py` 导入；不进入 Git。Harbor 初始化随机密钥、数据库密码和 token 签名证书保存在 `harbor-bootstrap`、`harbor-token-signing` 两个 Secret。备份必须包含这些 Secret 与数据库/镜像数据，避免单独恢复 PVC 后生成新密码。Git 仓库不包含这些凭据。

全新环境首次部署 Harbor 前，创建 harbor namespace 并运行 `python3 services/harbor/scripts/seed-secrets.py`（依赖 python3-bcrypt 和 OpenSSL）。RSA 签名私钥使用 Harbor 所需的 PKCS#1 格式；已有 PVC 时必须恢复原始凭据。

## 验证记录

所有 Argo CD 应用 Synced / Healthy；三个 HTTPS 地址通过系统 CA 校验。Harbor 登录及 `dockerhub/library/busybox:1.37.0` 实际拉取成功，registry API 确认缓存 artifact 已存在。入口已迁移为 Traefik + 每服务 Ingress，证书由各服务 Certificate 自动续期。

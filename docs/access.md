# 服务访问与网络边界

| 服务 | 当前内网地址 |
| --- | --- |
| Headlamp | https://headlamp.k8s.yhzone.top |
| Argo CD | https://argo-cd.k8s.yhzone.top |
| Harbor | https://harbor.k8s.yhzone.top |
| ZJULibBooking | https://zjulib.k8s.yhzone.top |
| NeverRun | https://neverrun.k8s.yhzone.top |

ExternalDNS 从各服务 Ingress 管理 Cloudflare DNS-only A 记录，内网服务域名均指向 `10.1.2.4`；原有 `*.k8s.yhzone.top` 泛解析保留。Traefik 以 hostNetwork 运行，仅监听首节点 EasyTier 地址 `10.1.2.4:443`，根据标准 Ingress 转发到集群 Service。需要加入 EasyTier 或有到该地址的路由才能访问。公网 20443 由独立 SNI/Traefik 入口接管，原 Docker Caddy 与 FRP 移至本机 21443，由 SNI 层转发，原服务外部地址保持 20443。

cert-manager 根据 Ingress 注解自动创建每服务的 Certificate，使用 Let's Encrypt ACME 和 Cloudflare DNS-01。TLS Secret 保存在各服务 namespace，Traefik 自动加载更新，无需手写 Caddyfile 或定时重载脚本。DNS 自检使用 DoH。新增服务见 [Ingress 配置](../services/traefik/README.md)。

## 登录

Headlamp 使用个人专用 ServiceAccount 的短期令牌；该账号为集群管理员，勿分享：

```sh
kubectl --context yihao -n headlamp create token yihao-admin --duration=1h
```

Headlamp 服务自身的 ServiceAccount 未授予 cluster-admin；用户需要主动登录。

长期管理员 Token 的 Secret 声明由 Argo CD 管理（`headlamp/yihao-admin-token`），实际 Token 由 Kubernetes 生成，不进入 Git。读取方式：

```sh
kubectl --context yihao -n headlamp get secret yihao-admin-token -o jsonpath='{.data.token}' | base64 -d; echo
```

此 Token 无固定过期时间，拥有 cluster-admin 权限。撤销时先从 Git 移除该资源声明并等待同步，再删除集群中的 Secret，避免自愈重新创建。

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

目前公开 Harbor：`https://harbor.yhzone.top:20443`，以及 ZJULibBooking：`https://zjulib.yhzone.top:20443`。A 为 ali-sas 公网 IPv4 `101.37.69.162`，AAAA 由手工 NodePublicIPv6 资源及实际服务后端节点决定。其余内网域名不在公网入口发布，公网 SNI 层拒绝 `*.k8s.yhzone.top`。

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

## ZJULibBooking

新公网地址 `https://zjulib.yhzone.top:20443`；原 `https://zjulib.d.yhzone.top:20443` 入口已移除。应用无数据库，任务仅在进程内存中，Pod 重启后需重新提交任务；浏览器 localStorage 不会自动迁移到新域名。镜像使用私有 Harbor 项目和独立只读 robot Secret，恢复集群时还需恢复 `zjulibbooking/harbor-pull`。

ZJULibBooking 的公网域名 `zjulib.yhzone.top` 需 Basic Auth，用户名为 `yihao`，密码使用用户指定值，仅保存 bcrypt 哈希。内网域名不增加此认证；Harbor 沿用原生认证。

## NeverRun 和 Hysteria2

NeverRun 公网入口 `https://neverrun.yhzone.top:20443`，沿用原 NeverRun Caddy 站点的 Basic Auth，凭据保存在 `neverrun/public-basic-auth`。旧 `neverrun.d.yhzone.top:20443` 入口已移除。内网入口不加 Basic Auth。

Hysteria2 为 UDP 服务，继续使用 30443 端口、既有域名和密码，IPv4 仍经 ali-sas 的 FRP 链路，IPv6 可直连首节点。其 `hysteria2/hysteria2-tls` Certificate 通过 Cloudflare DNS01 签发 `*.yhzone.top`，Secret 整目录挂载支持续期投射，Hysteria 在新 TLS 握手时读取证书。无需修改现有客户端配置。

## 新迁移的四个服务

| 服务 | 公网入口 | 内网入口 | 认证 |
| --- | --- | --- | --- |
| Subcon | https://subcon.yhzone.top:20443 | https://subcon.k8s.yhzone.top | 原 API token |
| Ascend Compiler Explorer | https://ascendc.yhzone.top:20443 | https://ascendc.k8s.yhzone.top | 沿用原配置 |
| FunASR Nano | https://funasr.yhzone.top:20443/health | https://funasr.k8s.yhzone.top/health | 实时接口使用原 Bearer API key |
| ZhiyunTools | https://zhiyun.yhzone.top:20443 | https://zhiyun.k8s.yhzone.top | 公网沿用原 Basic Auth |

FunASR 实时接口为 `wss://funasr.yhzone.top:20443/v1/realtime`。ZhiyunTools 通过集群 Service 访问 FunASR，不依赖公网绕行。四个旧 `.d.yhzone.top` 入口已移除；共享泛解析仍用于其他旧服务，旧域名可能返回网关默认响应。原订阅/API 客户端需要改用新地址；浏览器原站点数据不会自动复制到新域名。

持久数据均使用 `yihao-local` PVC，保存在 `~/k8s/storage/pvc/`。迁移前停写备份、原 Compose 配置及逐文件校验记录保存在 `~/k8s/storage/backups/migration-20260924/`（含敏感数据，不进入 Git）。原 Docker 数据与容器保留用于恢复。备份目前与业务数据同机。

## New API 与 Sub2API

New API 已迁移到 Kubernetes，原入口 **https://newapi.d.yhzone.top:20443** 保留；新增 https://newapi.yhzone.top:20443 和内网 https://newapi.k8s.yhzone.top。原认证、账号、API key、数据库及日志保留，旧入口经现有 Caddy 转接 Kubernetes。数据核验、备份和回退方法见 [New API](../services/new-api/README.md)。

Sub2API 按要求仅停用 Docker 应用、PostgreSQL 和 Redis，未迁入 Kubernetes。容器自动重启已关闭，Compose 使用 `disabled-manual-start` profile。原数据保留；逻辑备份、冷备份及校验清单位于 `~/k8s/storage/backups/sub2api-disabled-20260924/`。其旧入口当前不提供服务，不能把停止状态误认为已迁移。

## Vaultwarden

已迁移到 Kubernetes，保留 https://keys.yhzone.top:20443 和 https://keys.poc.pub:20443，经原 Caddy 入口转发至 Kubernetes。原账号、认证配置和客户端服务器地址保持不变。新增 https://vaultwarden.yhzone.top:20443 与内网 https://vaultwarden.k8s.yhzone.top。

完整数据冷备份位于 `~/k8s/storage/backups/vaultwarden-migration-20260924/`，原 Docker 数据保留、自动重启关闭。SQLite、配置和签名密钥已校验；详细存储和回退方法见 [Vaultwarden](../services/vaultwarden/README.md)。

## EasyTier Web

已迁入 Kubernetes，精确保留管理页面 `https://easytier.yhzone.top:20443` 与配置下发入口 `wss://easytier-rpc.yhzone.top:20443/<原客户端路径>`。原 Basic Auth、应用账号、客户端路径、端口和 Caddy 配置不变，客户端无需调整。Pod 接管原 loopback 11211/22020 端口；宿主机 EasyTier 组网服务保持独立运行。

迁移前完整数据及配置备份在 `~/k8s/storage/backups/easytier-web-migration-20260924/`，原 Docker 数据保留。详见 [EasyTier Web](../services/easytier-web/README.md)。


## 保留域名的公网 IPv4 转发

ali-sas 的 Kubernetes SNI 网关直接通过 EasyTier 转发到 `10.1.2.4:21443`，不再使用 FRPC 的 Caddy TCP 条目。EasyTier Web/WSS、New API、Vaultwarden 以及其他原 Caddy 站点的域名、端口和认证保持不变。旧域名的 TLS/HTTP 配置仍由原 Caddy 承载，未转换为每站点 Ingress。Hysteria2 的 UDP 30443 仍依赖 FRPC。

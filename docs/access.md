# 服务访问与网络边界

| 服务 | 当前内网地址 |
| --- | --- |
| Headlamp | https://headlamp.k8s.yhzone.top |
| Argo CD | https://argocd.k8s.yhzone.top |
| Harbor | https://harbor.yhzone.top |

Cloudflare DNS-only A 记录：`*.k8s.yhzone.top`、`harbor.yhzone.top` → `10.1.2.4`。当前公网入口未配置。Caddy 在集群中以 hostNetwork 运行，仅监听首节点 EasyTier 地址 `10.1.2.4:443`。原 Docker Caddy 的 20443 不变。需要加入 EasyTier 或有到该地址的路由才能访问。

cert-manager 使用 Let's Encrypt ACME 和 Cloudflare DNS-01，签发 `*.k8s.yhzone.top` 与 `harbor.yhzone.top` 证书。DNS 自检使用 DoH，避开本机透明代理的普通 DNS 缓存/拦截。Caddy 每 30 秒检查挂载的证书与配置，变化后执行强制热加载。私钥仅位于集群 Secret 和 Pod 只读挂载，不导出到 Docker Caddy。

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

`dockerhub` 为私有 Docker Hub 代理缓存项目，配额 30 GiB，匿名访问上游 Docker Hub。需先登录 Harbor：

```sh
docker login harbor.yhzone.top
docker pull harbor.yhzone.top/dockerhub/library/busybox:1.37.0
```

目前不改写 containerd 或其他节点的全局镜像源；使用上述前缀明确选择缓存。缓存项目由 `harbor-cache` Argo CD 应用的幂等 PostSync Job 配置。

镜像 PVC 请求 30 GiB、PostgreSQL 5 GiB、Redis 1 GiB、任务日志 1 GiB，均位于 `~/k8s/storage/pvc`。本地 PVC 大小不是文件系统硬配额；30 GiB 是 Harbor 项目的逻辑镜像配额，数据库、日志和上传临时文件另计。达到配额后需通过保留策略/垃圾回收释放空间，不保证自动 LRU 淘汰。Trivy 扫描器暂未启用。

## 后续公网入口

公网仅开放指定服务，外部端口 20443，不能直接把内网全部域名通配转发出去。Harbor 当前 externalURL 为 `https://harbor.yhzone.top`。部署公网 `:20443` 时需统一更新其 externalURL，并提供内网可达的同端口入口或其他经验证的认证转发方案；仅做端口映射可能导致 registry token realm 和重定向地址不匹配。

## 凭据恢复

Cloudflare 凭据从现有 Caddy compose 环境读取，用 `python3 bootstrap/import-cloudflare.py` 导入；不进入 Git。Harbor 初始化随机密钥、数据库密码和 token 签名证书保存在 `harbor-bootstrap`、`harbor-token-signing` 两个 Secret。备份必须包含这些 Secret 与数据库/镜像数据，避免单独恢复 PVC 后生成新密码。Git 仓库不包含这些凭据。

全新环境首次部署 Harbor 前，创建 harbor namespace 并运行 `python3 bootstrap/seed-harbor-secrets.py`（依赖 python3-bcrypt 和 OpenSSL）。RSA 签名私钥使用 Harbor 所需的 PKCS#1 格式；已有 PVC 时必须恢复原始凭据。

## 验证记录（2026-09-23）

所有 Argo CD 应用 Synced / Healthy；三个 HTTPS 地址通过系统 CA 校验。Harbor 登录及 `dockerhub/library/busybox:1.37.0` 实际拉取成功，registry API 确认缓存 artifact 已存在。Caddy 强制热加载已验证。首张证书到期时间为 2026-12-22，cert-manager 计划于 2026-11-22 续期。

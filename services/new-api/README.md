# New API

从 Docker 原实例迁移，固定原应用、PostgreSQL 15 和 Redis 8.10.0 镜像，使用本目录 Helm chart 由 Argo CD 管理。

## 入口

- 保留原公网地址：`https://newapi.d.yhzone.top:20443`。由 `new-api-legacy` 公网 Ingress 直接转发到应用 Service，不经过 Docker Caddy。
- 新公网地址：`https://newapi.yhzone.top:20443`。
- 内网地址：`https://newapi.k8s.yhzone.top`。

沿用应用原有认证，不额外增加 Basic Auth。`FRONTEND_BASE_URL` 保持旧公网地址，已有客户端与回调无需改域名。所有入口证书由 cert-manager 的 `letsencrypt-cloudflare` 签发。

## 数据与凭据

三个单副本 Deployment 固定在 `yihao-pve-debian`，更新策略为 Recreate。`yihao-local` 的 Retain PVC：应用数据/日志 5 GiB、PostgreSQL 10 GiB、Redis 1 GiB；实际路径位于 `~/k8s/storage/pvc/`，声明容量不是硬配额。Redis 原先使用容器可写层，现使用持久卷保留 RDB 快照。它仍采用原 RDB 持久化方式，并未启用 AOF。

`runtime-env`、`postgres-env`、`redis-env`、`harbor-pull` Secret 均在 Git 外导入，恢复时必须同时恢复原凭据。Service 名称 `postgres` / `redis` 保持原 DSN 和连接串可用。

2026-09-24 迁移前停止应用写入，生成最终 PostgreSQL 自定义格式逻辑备份、全局角色备份及 Redis SAVE 快照，再停止后端执行冷拷贝。备份目录：

`~/k8s/storage/backups/new-api-migration-20260924/`

目录含原 Compose、容器配置、Caddyfile、数据库备份、原始数据副本、SHA256 清单和实际 PVC 路径（`volumes.json`），含敏感数据，禁止提交 Git。冷拷贝校验通过；新数据库在应用启动前核对 34 张表的排序行摘要、229145 条记录和 29 个序列，与源库完全一致。65 个日志文件一并保留。Redis 目标目录/快照所有者调整为 999:999，内容不变；过期缓存键按原 TTL 自然过期。

原 Docker 三个容器已停止、restart=no，Compose 加入 `legacy-rollback` profile。原数据/卷保留。当前备份与业务数据同机。

## 回退

切勿直接启动旧 Compose：迁移后新写入仅在 Kubernetes PVC 中，原 Docker 数据已不再同步。

1. 先备份 Kubernetes 当前数据和 Secrets，并通过 Git 将应用 replicas 设为 0，等待应用停止写入。
2. 导出当前 PostgreSQL（pg_dump -Fc 和角色）及 Redis SAVE 快照，保存应用目录/日志；停止 Kubernetes 后端后再进行冷拷贝或恢复。
3. 将最新数据恢复到原 Docker 数据路径/卷，保留匹配版本、所有者和原凭据。只有明确接受丢弃切换后的写入时，才能直接使用迁移前备份。
4. 使用 `docker compose --profile legacy-rollback up -d` 启动原 Compose，检查健康后恢复对应 Caddy 站点（upstream `127.0.0.1:24313`），并从公网 Ingress 撤销旧域名路由以使 SNI 回退生效；验证配置并 reload。不要用整份历史 Caddyfile 覆盖其他站点的新变更。
5. 若同时停用新公网入口，在 Git 中停用发布，并按仓库不自动 prune 的约定显式清理对应网络资源；不要删除数据 PVC。

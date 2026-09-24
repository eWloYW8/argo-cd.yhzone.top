# EasyTier Web

将原 Docker `easytier-web` 迁入 Kubernetes，保持 `easytier-web 2.5.0-88a45d11` 原镜像内容，使用私有 Harbor digest 固定版本。本服务由本地 Helm chart 与 Argo CD 管理，单副本 Recreate，固定首节点 `yihao-pve-debian`。宿主机上的 EasyTier 组网服务独立运行，本次未变更。

## 原入口与连接方式

- 管理页面：`https://easytier.yhzone.top:20443`，保留原 Caddy Basic Auth 和应用账号认证。
- 配置下发/RPC：`wss://easytier-rpc.yhzone.top:20443/<原客户端路径>`，保留现有客户端用户名路径及 WebSocket 协议，不增加 Basic Auth。
- `WEB_DEFAULT_API_HOST=https://easytier.yhzone.top:20443`、全部端口和其他原环境配置不变。

Pod 通过限定 `hostIP: 127.0.0.1` 的 hostPort 接管首节点原 `11211/TCP`（页面/API）和 `22020/TCP`（WS 配置服务）。原 Caddy upstream、认证、请求头处理、DNS、证书及 FRP/SNI 链路全部保持不变，不注册覆盖现有入口的公网 Ingress。集群内另提供同端口 ClusterIP Service `easytier-web`。

保留此入口方式是为了使现有节点准确重连；不能同时启动原 Docker 容器，否则端口冲突。原 Basic Auth 仅在 Caddy 上管理。页面公网端口仍为 20443，Caddy 本地接入端口为 21443。

## 持久化与备份

5 GiB `yihao-local` Retain PVC `easytier-web-data`，实际数据路径位于 `~/k8s/storage/pvc/`，完整挂载 `/app/data`。声明容量不是硬配额。SQLite `et.db`、配套 WAL、日志等完整迁移。

迁移备份目录：`~/k8s/storage/backups/easytier-web-migration-20260924/`（0700，含敏感数据，禁止提交 Git）。包含原 Compose/容器配置、完整 data 冷备份、独立 SQLite backup API 数据库备份、文件 SHA256/权限清单、逐表内容摘要、目标 PVC 路径、原 Caddyfile 和 Kubernetes Secrets。备份当前与业务数据同机。

2026-09-24 停写后复制并核验 14 个文件。数据库 9 张表共 66 条记录（含 3 个用户、46 条已保存网络配置），SQLite integrity_check 通过；源数据库、恢复库和独立备份的逐表内容摘要一致。新实例启动后再次核对全部表，仍一致。原 Caddyfile 与备份逐字节一致，管理页面 HTML SHA256 亦不变。公网 IPv4/首节点 IPv6 的页面认证返回 401、RPC WebSocket 握手返回 101 均已验证；IPv6 测试由首节点发起。

`runtime-env` 与 `harbor-pull` Secret 在 Git 外导入；前者保存原镜像默认值之外的运行环境，后者为只读拉取凭据。应与数据一并备份。

## 回退

原 Docker 容器停止、restart=no，原 Compose 加入 `legacy-rollback` profile，原数据目录不删除。迁移后新增配置只写 Kubernetes 数据，原目录不再同步。

1. 在 Git 将 replicas 设为 0，并等待 Pod 完全退出，以停止写入并释放两个 hostPort。
2. 对最新 PVC 完整冷备份，再将最新数据恢复到原 Docker 数据目录，保持所有者/权限。SQLite 数据库与 WAL 必须配套恢复；恢复独立 SQLite backup 文件时不得混用旧 WAL/SHM。
3. 用 `docker compose --profile legacy-rollback up -d` 启动原实例。无需修改 Caddy，随后检查页面认证、RPC WebSocket 握手和节点重连。
4. 切勿并行运行两个可写实例，或不经确认直接用迁移前旧库覆盖切换后的数据。PVC 不应删除。

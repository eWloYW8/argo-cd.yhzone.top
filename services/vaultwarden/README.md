# Vaultwarden

原 Docker Vaultwarden 1.36.0-46ae59ea（Web Vault 2026.6.4）按原镜像内容迁移，Harbor 私有项目固定 digest，未同时升级。使用本地 Helm chart、Argo CD、单副本 Recreate，固定首节点 `yihao-pve-debian`。

## 访问

- 保留 `https://keys.yhzone.top:20443`，通过 `vaultwarden-legacy` 公网 Ingress 直达应用 Service，支持 WebSocket，不经过 Docker Caddy。`keys.poc.pub` 已移除并由 SNI 网关拒绝。
- 新公网入口 `https://vaultwarden.yhzone.top:20443`；内网 `https://vaultwarden.k8s.yhzone.top`。全部 Kubernetes 域名证书由 cert-manager / Cloudflare DNS01 管理。
- 原 `config.json` 的 domain 仍为 `https://keys.yhzone.top:20443`，客户端无需修改服务器地址。账号、两步验证、管理配置和 SMTP 配置保持原样，不额外增加 Basic Auth。

## 数据

`vaultwarden-data` 使用 5 GiB `yihao-local` Retain PVC，数据位于 `~/k8s/storage/pvc/`，挂载 `/data`。容量声明不是文件系统硬配额。SQLite、签名私钥、配置、缓存、临时文件及存在的附件/Send 目录均应完整保留。配置包含敏感值，仅在 PVC 与受限备份中保存，不能提交 Git。

`runtime-env` 为原容器环境差异，`harbor-pull` 为私有项目只读 robot 凭据，均在 Git 外管理。

2026-09-24 停止旧应用写入后，完整冷拷贝 171 个文件，源目录、备份、PVC 的 SHA256 和所有者/权限核验一致。SQLite integrity_check 通过，29 张表共 800 行的逐表内容摘要一致；另用 SQLite backup API 生成独立数据库备份并验证。新应用启动后、旧入口切换前再次核对全部表、签名私钥与配置，内容未变。

备份路径：`~/k8s/storage/backups/vaultwarden-migration-20260924/`。含完整 `data/`、独立 `database.sqlite3`、文件/数据库摘要、实际 PVC 路径、原 Compose / Docker 配置与 Caddyfile。目录权限 0700，含敏感数据；备份与业务数据同机。原 Docker 数据不删除，容器停止且自动重启关闭，Compose 使用 `legacy-rollback` profile。

## 回退与恢复

切换后原 Docker 数据不再同步。回退前先暂停入口写入，在 Git 中将 replicas 设为 0，等待 Pod 完全停止，并备份最新完整 PVC 数据及 Secrets。将最新数据恢复到原 Docker `/data` 目录，保留权限，避免同时运行两个可写实例。使用 `docker compose --profile legacy-rollback up -d`，验证后恢复对应 Caddy 站点（upstream `127.0.0.1:20456`）并从公网 Ingress 撤销其旧域名路由，再 validate/reload；不要覆盖其他站点变更。迁移前备份只能恢复到迁移时间点。

冷拷贝的 SQLite 数据库和 WAL 必须配套恢复；使用独立 SQLite backup 文件恢复时，不得混用旧 WAL/SHM。参见 [Vaultwarden 官方备份文档](https://github.com/dani-garcia/vaultwarden/wiki/Backing-up-your-vault)。

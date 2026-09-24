# 维护

## 登录

Argo CD、Headlamp、Harbor 的内网域名分别为 `argo-cd.k8s.yhzone.top`、`headlamp.k8s.yhzone.top`、`harbor.k8s.yhzone.top`。Argo CD CLI 使用 `--grpc-web`。

Headlamp 使用 `yihao-admin`，拥有 cluster-admin 权限。临时令牌：

```sh
kubectl --context yihao -n headlamp create token yihao-admin --duration=1h
```

长期令牌由 `headlamp/yihao-admin-token` Secret 生成。撤销前先移除 Git 声明，再删除集群 Secret，避免自愈重建。

Argo CD 和 Harbor 用户名均为 `admin`。下列命令只在自己的终端执行，不将结果贴入日志或 Git：

```sh
kubectl --context yihao -n headlamp get secret yihao-admin-token -o jsonpath='{.data.token}' | base64 -d
kubectl --context yihao -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d
kubectl --context yihao -n harbor get secret harbor-bootstrap -o jsonpath='{.data.HARBOR_ADMIN_PASSWORD}' | base64 -d
```

Argo CD 初始密码仅在尚未修改时有效。

## 存储与恢复

`yihao-local` 在首节点提供 Retain 本地卷，数据位于 `~/k8s/storage/pvc`。PVC 容量不是文件系统硬配额，也没有跨节点复制。

Shell 文件直接编辑 `~/k8s/storage/shell`，对应 `https://shell.yhzone.top:20443/<文件名>`，增删立即生效。大文件先在同一文件系统的站外目录写完，再移动进去，避免下载到半成品。

备份位于 `~/k8s/storage/backups`，etcd 快照位于 `~/k8s/storage/etcd-snapshots`。同盘备份不能应对磁盘故障；恢复还需要应用数据、Secret、K3s server token。旧 Docker 数据只是迁移时的快照，回退必须先停止当前写入并迁回最新数据，不能同时运行两个可写实例。

| 服务 | 恢复时需要一起保留的内容 |
| --- | --- |
| Vaultwarden | 完整 `/data`：SQLite、配置、签名密钥、附件；冷拷贝须保留配套 WAL，独立 SQLite backup 不混用旧 WAL/SHM |
| New API | PostgreSQL 数据及角色、Redis RDB、应用目录、匹配的密码；Redis 未启用 AOF |
| EasyTier Web | 数据库与配置；节点实例 ID 和本地组网配置不可重新生成 |
| ZhiyunTools | `zhiyun.db`、`settings.json`、`credentials.key`；缺少密钥无法解密已存凭据 |
| Subcon | conf 和自定义 schemas；启动会清理缓存 |
| Ascend Compiler Explorer | 存储目录和编译缓存；镜像含 CANN 工具链，不能用普通基础镜像替换 |
| FunASR Nano | `/models` 只读模型与 API 凭据；当前 CPU 镜像针对首节点构建 |

ZJULibBooking 的任务在进程内存中，重启会丢失；浏览器设置在 localStorage，不随域名迁移。NeverRun 无服务端持久库。ZJU-Autosign 的通知去重状态重启后重置；运行状态不代表上游登录成功，需检查应用日志。

ZhiyunTools 经集群 Service 访问 FunASR，恢复配置时不要换回已撤销的旧公网地址。Vaultwarden 保留 `keys.yhzone.top:20443`，New API 保留 `newapi.d.yhzone.top:20443`；原客户端和回调仍使用这些地址。

## Secret

业务凭据由[私有仓库](https://github.com/eWloYW8/argo-cd-secrets.yhzone.top)的 `yihao-secrets` Application 管理，仅允许部署 Secret。文件按命名空间分目录，使用未加密的 Base64 `data`；自动 prune 和 Secret 删除均关闭。改动环境变量或 subPath 挂载的 Secret 后，需要重启使用它的应用。

新集群必须先恢复私有仓库只读部署密钥，再同步 Secret。密钥位于本机 `~/k8s/.bootstrap/repo-split/secrets-deploy-key` 和集群 `argocd/yihao-secrets-git-repository`，不在任一 Git 仓库中；也可重新注册只读 deploy key。字段清单见 [secret-inventory.yaml](../bootstrap/secret-inventory.yaml)。

证书、ACME 账户、ServiceAccount token 由控制器生成，不纳入业务 Secret 仓库。Hysteria2 证书使用整目录挂载，不改成 subPath，否则续期文件不能自动更新。

## 镜像

普通镜像使用 `harbor.k8s.yhzone.top/<上游>/<镜像>`。这是 Kustomize 前缀，不是节点全局镜像源；GitOps 外的 Pod 不会自动改写。启动基础组件直连上游，避免恢复时依赖 Harbor 自身。

缓存项目和总计 30 GiB 的配额见 [cache-config.json](../services/harbor/resources/cache-config.json)，由 PostSync Job 配置。配额不提供自动 LRU，需要保留策略与垃圾回收。自建镜像放私有 hosted 项目，使用命名空间内的只读拉取凭据。

Harbor 的认证 realm 为 `https://harbor.yhzone.top:20443`，使用内网镜像前缀的客户端也需要能访问该认证地址。

## 节点启动

EasyTier Web 位于集群内，宿主机 EasyTier 必须能离线组网，否则会形成启动循环依赖。每个节点的原实例配置保存在 `/etc/easytier/config.d/<实例ID>.toml`（目录 0700、文件 0600），由 [systemd drop-in](../bootstrap/easytier/20-local-config-cache.conf) 设置 `ET_CONFIG_DIR`。恢复时保留节点自己的实例 ID，不复制其他节点的 TOML。此设置未做整机重启验证；启用自动保存前，组网变更需同步更新本地快照。

ali-sas 使用 [独立 agent 配置](../bootstrap/nodes/ali-sas/config.yaml)，不能复制首节点的 cluster-init 配置。安装路径为 `/etc/rancher/k3s/config.yaml`，token 位于 `/etc/rancher/k3s/agent-token`；K3s 等待 EasyTier 就绪后启动。预留内存较多，增加负载前检查实际可用量。

ali-sas 的 `/var/lib/rancher/k3s/agent/images/` 保留 `pause.tar` 和 `public-edge.tar`，避免启动依赖 Docker Hub 或 Harbor；升级时同步所需镜像。更换同名节点需处理旧节点和 `/etc/rancher/node/password` 身份。

首节点为 PVE LXC，内核参数需要在 PVE 宿主机配置。`/dev/kmsg` 使用 console 兼容链接，OOM 观测有限；NetworkManager 的 CNI 排除配置位于 [bootstrap/k3s](../bootstrap/k3s)。

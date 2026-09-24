# 仓库约定

- 使用 Conventional Commits；kubectl 写操作显式指定 `--context yihao`。
- 本仓库公开，禁止提交凭据、私钥、kubeconfig 或渲染后的 Secret。未加密 Secret 只放私有 `eWloYW8/argo-cd-secrets.yhzone.top`；仓库访问密钥留在 Git 外。
- 一个服务一个 `services/<服务>/`，包含 `app.yaml` 与 `kustomization.yaml`。服务资源和脚本留在对应目录，`bootstrap/` 只放主机与集群启动配置。
- Chart、镜像固定版本；上游完整 values 使用 `values/<chart>-<version>.yaml`。下载的 `charts/` 不提交，自定义 Chart 放 `helm/`。
- 修改清单后运行 `kubectl --context yihao kustomize --enable-helm services/<服务>`；不输出凭据。不从参考仓库复制密钥或环境专属配置。
- 数据使用 `yihao-local`。接管 Secret 时保留名称和原值；自动 prune 关闭，不擅自删除数据。

## 镜像与网络

- 普通服务引用 `../../components/image-prefix`，渲染后只加一次 `harbor.k8s.yhzone.top/`。Docker Hub 短名先规范化为 `docker.io/library/<镜像>` 或 `docker.io/<组织>/<镜像>`。
- 自建镜像使用 Harbor 私有项目和命名空间内的只读拉取凭据，不推入代理缓存项目。缓存配额见 `services/harbor/resources/cache-config.json`。
- Harbor 及其数据库/初始化任务、Traefik、cert-manager、ExternalDNS、本地存储、public-network、hysteria2-udp-gateway 和 K3s 组件直接使用上游镜像，避免启动循环依赖。
- 内网使用 `traefik`、`*.k8s.yhzone.top:443`；公网使用 `traefik-public`、显式 exposure 标签和 20443。公网拒绝内网域名。
- `NodePublicIPv6` 必须人工声明，不自动发现或登记地址。AAAA 要求授权、节点、网关和本机服务后端均就绪。
- 公网后端使用独立 Service、NativeLB 和 PreferSameNode，DNS 由 DNSEndpoint 发布。保留 SNI 到 `10.1.2.4:21443` 的旧 Caddy 回退，不将公网全量导向内网 Ingress。

## 文档

默认更新现有 README 或 docs，不为每个服务新增说明。只保留配置无法直接表达的原因、依赖和恢复要点；不重复 YAML，不堆迁移过程、验证流水账和模板化总结。短句、具体事实，避免宣传性措辞。

# Harbor 镜像前缀

默认入口为 `https://harbor.k8s.yhzone.top`，旧 `harbor.yhzone.top` 保留为兼容入口；登录账号和数据不变。Harbor externalURL 与 registry token realm 使用新域名。

参考 zjusct 仓库，用 Kustomize PrefixTransformer 在渲染时添加 `harbor.k8s.yhzone.top/`。共用组件位于 `components/image-prefix/`，覆盖普通工作负载、initContainers、CronJob 和 Pod 的镜像字段。

普通服务的 `kustomization.yaml` 加入：

```yaml
components:
- ../../components/image-prefix
```

镜像原名必须带上游 registry，例如 `quay.io/argoproj/argocd:v3.5.3`；短名先规范化到完整名称。Docker Hub 官方镜像需要 `docker.io/library/`：

```yaml
images:
- name: nginx
  newName: docker.io/library/nginx
```

应用组件后检查渲染结果，避免重复前缀。当前 Argo CD 与 Headlamp 已采用此前缀。Harbor（含数据库与初始化任务）、Traefik、cert-manager、ExternalDNS、本地存储及 K3s 自带组件直连上游，避免 Harbor 恢复依赖自身或入口、证书、DNS、存储依赖 Harbor 的循环。

这是 GitOps 清单默认约定，不是 admission 强制策略，也不是修改节点 containerd/Docker 全局镜像源；仓库外直接部署的 Pod 不会自动改写。

## 缓存项目

配置声明于 `resources/cache-config.json`，PostSync Job 幂等创建上游端点、项目并设置配额。上游均未配置私有凭据。

| 前缀项目 | 上游 | 配额 | 拉取权限 |
| --- | --- | --- | --- |
| docker.io | Docker Hub | 10 GiB | 匿名 |
| quay.io | Quay | 8 GiB | 匿名 |
| ghcr.io | GHCR | 5 GiB | 匿名 |
| registry.k8s.io | Kubernetes Registry | 3 GiB | 匿名 |
| public.ecr.aws | ECR Public | 2 GiB | 匿名 |
| dockerhub | 原有 Docker Hub 缓存 | 2 GiB | 登录 |

总配额为 30 GiB，原 dockerhub 项目数据保留，原独占的 30 GiB 配额改为按上游分配。底层 registry PVC 仍为 30 GiB，数据库等另计；本地卷的容量声明不是文件系统硬限额，不提供自动 LRU 淘汰。

```sh
docker pull harbor.k8s.yhzone.top/docker.io/library/busybox:1.37.0
docker pull harbor.k8s.yhzone.top/quay.io/argoproj/argocd:v3.5.3
```

公共缓存项目只能拉取上游公开镜像；普通应用无需 imagePullSecrets。原私有 dockerhub 项目仍需登录。管理登录：

```sh
docker login harbor.k8s.yhzone.top
kubectl --context yihao -n harbor get secret harbor-bootstrap \
  -o jsonpath='{.data.HARBOR_ADMIN_PASSWORD}' | base64 -d
```

用户名为 admin；不要将密码写入 Git。

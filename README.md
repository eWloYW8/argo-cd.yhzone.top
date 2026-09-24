# argo-cd.yhzone.top

个人 K3s 集群的 GitOps 配置，context 为 `yihao`。节点通过 EasyTier 互联。

| 节点 | EasyTier 地址 | 用途 |
| --- | --- | --- |
| yihao-pve-debian | 10.1.2.4 | 控制平面、应用、本地存储 |
| ali-sas | 10.1.2.2 | 公网 IPv4 入口、worker |

## 仓库

- `services/<服务>/`：一个服务一个目录，`app.yaml` 供 ApplicationSet 发现，`kustomization.yaml` 组合 Helm 和资源。
- `clusters/yihao/`：根 Application、ApplicationSet、Secret Application。
- `components/image-prefix/`：普通服务的 Harbor 镜像前缀。
- `bootstrap/`：主机配置和集群启动资料。
- [私有 Secret 仓库](https://github.com/eWloYW8/argo-cd-secrets.yhzone.top)：未加密的业务凭据，由 `yihao-secrets` 同步。本仓库公开，不存凭据。

Argo CD 自动同步、自愈，不自动 prune。删除 Git 文件后，仍需显式删除集群资源；命名空间和 Secret 另有删除保护。控制器生成的证书、PV、DNS 输出不重复声明。

修改服务后先渲染，再按 Conventional Commits 提交：

```sh
kubectl --context yihao kustomize --enable-helm services/<服务>
```

需要 Helm。Chart 和镜像固定版本，下载的 `charts/` 不提交；自定义 Chart 放在 `helm/`。渲染结果可能包含 Secret，不公开输出。

## 运维

- [网络](docs/network.md)：内外网入口、DNS、证书、IPv6 登记。
- [维护](docs/operations.md)：登录、存储、凭据恢复、节点启动依赖。

文档只记配置中看不出的依赖和维护要点。版本、端口、资源配额以清单为准，变更过程查 Git 历史。

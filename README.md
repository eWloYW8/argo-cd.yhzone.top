# argo-cd.yhzone.top

个人 Kubernetes 配置仓库，使用 Argo CD、Kustomize 和 Helm 管理。

- `services/`：按应用组织配置。
- `clusters/`：Argo CD 同步入口。
- `components/`：共享配置。

修改后检查渲染结果：

```sh
kubectl kustomize --enable-helm services/<应用>
```

需要安装 Helm。版本固定在配置中，提交遵循 Conventional Commits。凭据和运维资料不在本公开仓库保存。

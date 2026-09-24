# ExternalDNS

Helm Chart 1.22.0 / ExternalDNS 0.22.0，由 ApplicationSet 自动部署。

只监听带 `dns.yhzone.top/managed: "true"` 注解的 Service / Ingress；域名限定为 `k8s.yhzone.top` 与 `harbor.yhzone.top`，Cloudflare zone 固定为 `yhzone.top`。采用 `sync` 策略及 TXT registry，owner 为 `yihao`、TXT 前缀为 `_external-dns.`，默认每分钟同步，也响应资源事件。

## 服务声明

在服务自己的 Kustomize patch 或 Helm values 中添加 Service 注解：

```yaml
metadata:
  annotations:
    dns.yhzone.top/managed: "true"
    external-dns.kubernetes.io/hostname: example.k8s.yhzone.top
    external-dns.kubernetes.io/target: 10.1.2.4
    external-dns.kubernetes.io/ttl: "300"
    external-dns.kubernetes.io/cloudflare-proxied: "false"
```

目标必须是可达入口地址。当前由 Caddy 监听 EasyTier 10.1.2.4:443；新增 HTTP 服务还需要配置 Caddy 路由，ExternalDNS 不解析 Caddyfile，也不配置端口。

删除集群资源或移除其 DNS 注解后，对应的受管 DNS 记录会自动删除。Argo CD 自动 prune 关闭，仅删除 Git 文件不会删除已有 Kubernetes 资源，需要显式同步删除。原有 `*.k8s.yhzone.top` 泛解析保留且不归本控制器管理，因此单条记录删除后该域名仍可能通过泛解析解析。

## 凭据

运行 `python3 services/external-dns/scripts/import-cloudflare.py`，从 cert-manager 的现有 Secret 安全复制凭据到 external-dns namespace。凭据不进入 Git；轮换后重新运行脚本并重启 ExternalDNS Deployment。Cloudflare token 需要该 zone 的 Zone Read / DNS Edit 权限。

已有无 TXT 所有权的记录不会被自动接管。迁移时先核对现有目标，并为指定记录建立正确的 TXT owner；禁止使用 noop registry 或批量接管整个 zone。Harbor 原有 A 记录按此方式保留接管。

参考：https://kubernetes-sigs.github.io/external-dns/latest/docs/tutorials/cloudflare/

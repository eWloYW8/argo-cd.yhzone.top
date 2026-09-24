# ExternalDNS

Helm Chart 1.22.0 / ExternalDNS 0.22.0，由 ApplicationSet 自动部署。

只监听带 `dns.yhzone.top/managed: "true"` 注解的 Service / Ingress；域名限定为 `k8s.yhzone.top`，Cloudflare zone 固定为 `yhzone.top`。采用 `sync` 策略及 `noop` registry，不生成所有权 TXT 记录，默认每分钟同步，也响应资源事件。

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

目标必须是可达入口地址。当前由 Traefik 监听 EasyTier 10.1.2.4:443。HTTP 服务优先在自己的 Ingress 上配置这些注解，域名来自 spec.rules / spec.tls；无需给后端 Service 重复添加注解，ExternalDNS 不配置端口。参见 [Ingress 示例](../traefik/README.md)。

删除集群资源或移除其 DNS 注解后，对应的受管 DNS 记录会自动删除。Argo CD 自动 prune 关闭，仅删除 Git 文件不会删除已有 Kubernetes 资源，需要显式同步删除。原有 `*.k8s.yhzone.top` 泛解析由 `resources/internal-wildcard.yaml` 中的无后端 Service 声明并纳入同步；该 Service 仅声明 DNS，实际流量仍进入 Traefik。因此单条记录删除后该域名仍可能通过泛解析解析。

## 凭据

运行 `python3 services/external-dns/scripts/import-cloudflare.py`，从 cert-manager 的现有 Secret 安全复制凭据到 external-dns namespace。凭据不进入 Git；轮换后重新运行脚本并重启 ExternalDNS Deployment。Cloudflare token 需要该 zone 的 Zone Read / DNS Edit 权限。

`k8s.yhzone.top` 范围内的 A / AAAA / CNAME 全部交由此控制器同步，没有对应 Kubernetes 声明的记录会被删除，包括手工添加的记录。资源注解只筛选 Kubernetes 来源，不保护 DNS 提供商中的现有记录。不要扩大域名范围。公网仍由独立 external-dns-public 使用 `txt + sync` 管理，不受本次变更影响。

参考：https://kubernetes-sigs.github.io/external-dns/latest/docs/tutorials/cloudflare/

# 网络

| 入口 | 路径 |
| --- | --- |
| 内网 HTTPS | `*.k8s.yhzone.top:443` → EasyTier `10.1.2.4` → Traefik |
| 公网 IPv4 HTTPS | `*.yhzone.top:20443` → ali-sas `101.37.69.162` → HAProxy → 公网 Traefik |
| 公网 IPv6 HTTPS | AAAA → 有服务后端的授权节点 → 该节点公网入口 |
| Hysteria2 IPv4 | ali-sas UDP 30443 → 独立 UDP 网关 → Hysteria2 Service |
| Hysteria2 IPv6 | 首节点 UDP 30443，直接连接 |

公网 HAProxy 按 SNI 分流，Traefik 监听本机 20444。两者之间使用 PROXY v2，Traefik 只信任 loopback。只提供 TCP HTTPS，不提供 HTTP/3。

未匹配的公网域名回退到首节点 Caddy `10.1.2.4:21443`，目前仅保留 Mihomo、动态代理及通配兜底；FRPC 已停用。公网拒绝 `*.k8s.yhzone.top` 和已撤销的 `keys.poc.pub`。

## 发布服务

内网 Ingress 使用 class `traefik`、注解 `dns.yhzone.top/managed: "true"` 和目标 `10.1.2.4`。证书 issuer 为 `letsencrypt-cloudflare`。参考 [Harbor 内网入口](../services/harbor/resources/ingress.yaml)。

公网使用独立 Service 和 Ingress：class 为 `traefik-public`，标签为 `networking.yhzone.top/exposure: public`；Service 开启 `traefik.ingress.kubernetes.io/service.nativelb` 和 `trafficDistribution: PreferSameNode`。参考 [Harbor 公网入口](../services/harbor/resources/ingress-public.yaml)。不要添加内网 DNS 注解。

公网支持单层 `服务.yhzone.top` 和保留的 `服务.d.yhzone.top`。Basic Auth 由同命名空间 Middleware 按需启用，不设全局认证。

新入口先申请证书，再添加 exposure 标签。`networking.yhzone.top/publish-dns: "false"` 只暂停 DNS 发布，不能阻止 SNI 路由接入。

## DNS 与证书

- 内网 ExternalDNS：`k8s.yhzone.top`，`noop + sync`。范围内没有 Kubernetes 声明的 A/AAAA/CNAME 会被删除；泛解析由 [Service 声明](../services/external-dns/resources/internal-wildcard.yaml)保留。
- 公网 ExternalDNS：读取 public-network 生成的 DNSEndpoint，`txt + sync`，owner 为 `yihao-public`。保留 `_external-dns-public.` 所有权 TXT。
- cert-manager 使用 Cloudflare DNS-01，无需开放 HTTP 80。TLS Secret 由控制器续期，Ingress 自动加载。

## IPv6

在 `services/public-network/resources/` 手工添加 `NodePublicIPv6` 并加入 Kustomize；资源名等于 Node 名称。参考 [首节点声明](../services/public-network/resources/yihao-pve-debian-ipv6.yaml)。地址必须稳定且能从公网访问 20443，控制器不探测外网可达性。

AAAA 只选同时满足授权、Ready Node、Ready 网关、Ready 本机后端的节点；多后端 Ingress 取节点交集。NativeLB 和 PreferSameNode 是发布 AAAA 的前提，本机后端不可用时仍可跨节点转发。

撤销地址时先在 Git 设置 `enabled: false`。退役网关需等待 DNS 缓存过期，再移除节点的 `networking.yhzone.top/public-gateway` 标签；控制器不会立即清除该标签。DNS 更新不是即时故障切换。

```sh
kubectl --context yihao get nodepublicipv6s
kubectl --context yihao -n public-network get dnsendpoints
```

Hysteria2 的 UDP 网关独立部署在 ali-sas，避免与首节点同端口监听冲突。TLS 和认证仍由后端处理；网关健康检查不代表客户端认证成功。

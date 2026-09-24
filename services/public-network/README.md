# 公网入口与手工 IPv6 授权

## 已部署拓扑

- 内网：`服务.k8s.yhzone.top:443` → EasyTier `10.1.2.4` → 原 Traefik（IngressClass `traefik`）。
- 公网 IPv4：`服务.yhzone.top:20443` → `101.37.69.162` / ali-sas → SNI edge → 本机公网 Traefik → 集群 Service / Pod。
- 公网 IPv6：同一域名的 AAAA → 有 Ready 后端且经手工授权的节点 IPv6 → 该节点公网入口 → 优先本机 Pod。

公网入口是 `traefik-public` DaemonSet，每个已登记入口节点上包含 HAProxy SNI 分流与 Traefik。Traefik 只监听 loopback `20444`，健康检查 `18081`；HAProxy 对外监听 TCP `20443`。只有 `IngressClass=traefik-public` 且带 `networking.yhzone.top/exposure: public` 标签的路由会接入公网。内网域名在 SNI 层直接拒绝。

旧服务继续走 `20443`：没有匹配 Kubernetes 公网路由的连接转交本机 `21443`；ali-sas 上为 FRPS 的旧 Caddy 转发，首节点上为 Docker Caddy。旧 Caddy/FRPC 配置已移到 21443，云网卡 eth0 上的 21443 由 systemd 防火墙规则禁止直接访问，见 `bootstrap/public-edge/legacy-firewall.service`。这一步是一次性主机迁移；新增 Kubernetes 服务不再编辑 Caddyfile 或 FRP。

PROXY v2 仅用于本机 SNI edge → 公网 Traefik，Traefik 只信任 loopback 来源；公网 Kubernetes 服务可获得原客户端地址。旧 FRP 链路保持原有客户端地址行为。公网入口目前为 TCP HTTPS，不提供 HTTP/3。

## 手工登记节点 IPv6

资源为集群级 `NodePublicIPv6`，metadata.name 必须等于 Node 名称。**控制器没有创建、修改 spec 或删除该资源的 RBAC 权限，不自动探测、登记 IPv6。** 初始首节点由明确的人工 Git 清单 `resources/yihao-pve-debian-ipv6.yaml` 登记：

```yaml
apiVersion: networking.yhzone.top/v1alpha1
kind: NodePublicIPv6
metadata:
  name: yihao-pve-debian
spec:
  address: 2001:da8:e000:731a:be24:11ff:fe21:c6f6
  enabled: true
```

ali-sas 当前没有公网 IPv6，因此没有此资源。新增节点可复制 `examples/node-ipv6.yaml`，填写真实 Node 名称和稳定的全球单播 IPv6；示例文档地址不可发布。推荐将手工填写的资源放入本服务 resources 并加入 kustomization。也可由管理员直接 `kubectl --context yihao apply -f ...` 登记，但需要自行备份。

登记前由管理员确认：地址属于该节点、不是临时隐私地址、外部 IPv6 客户端可以访问 TCP 20443、主机及上游防火墙允许连接。控制器做地址范围、节点及入口就绪检查，不代替外网可达性探测。地址变更必须手工更新；即使 Node 报告了其他 IPv6，没有该资源也不会自动产生 AAAA。

```sh
kubectl --context yihao get nodepublicipv6s
kubectl --context yihao get nodepublicipv6 yihao-pve-debian -o yaml
kubectl --context yihao -n public-network get dnsendpoints
```

删除资源或设置 `spec.enabled: false` 撤销对应 IPv6 授权。已由 Git 管理的资源需同步修改 Git，否则 Argo CD 会恢复原值；自动 prune 关闭，删除 Git 文件后还需显式删除集群对象。`status.publishedHosts` 显示当前对应 AAAA 域名。

## 服务发布

在服务自己的目录中保留内网 Ingress，增加独立的公网 Service 和 Ingress。可参考 Harbor 的 `resources/ingress-public.yaml`：

```yaml
apiVersion: v1
kind: Service
metadata:
  name: example-public
  annotations:
    traefik.ingress.kubernetes.io/service.nativelb: "true"
spec:
  selector:
    app: example
  trafficDistribution: PreferSameNode
  ports:
  - port: 80
    targetPort: 8080
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-public
  labels:
    networking.yhzone.top/exposure: public
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-cloudflare
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
spec:
  ingressClassName: traefik-public
  tls:
  - hosts: [example.yhzone.top]
    secretName: example-public-tls
  rules:
  - host: example.yhzone.top
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example-public
            port:
              number: 80
```

公网 Ingress 不添加内网 ExternalDNS 的 `dns.yhzone.top/managed` 注解。仅支持 `服务.yhzone.top` 单层、非通配域名。`networking.yhzone.top/publish-dns: "false"` 可暂缓 DNS 发布以便先验证入口。域名重复声明会暂停该域名的 DNS 发布，应确保唯一。

`PreferSameNode` + NativeLB 让 kube-proxy 优先本机后端，但这是偏好而非硬性约束；当本机后端迁移/消失时可跨节点转发。一个域名有多个 Service 后端时，只有同时拥有这些 Service Ready 后端的节点才进入 AAAA 候选。

## 控制与 DNS

控制器每 10 秒读取 Ingress、Service、EndpointSlice、Certificate、Node 和手工 IPv6 资源：

1. 将 ali-sas 和经手工资源授权的节点标记为公网入口节点，由 DaemonSet 启动入口。
2. 从明确标记的公网 Ingress 更新 HAProxy 路由 ConfigMap；挂载更新后自动校验、平滑重载。
3. 证书 Ready 后生成受管 DNSEndpoint：A 固定为 ali-sas IPv4；AAAA 取手工 IPv6 资源、Ready Node、Ready 公网入口、服务 Ready 后端节点的交集。缺少本机优先 Service 配置时只发布 A。
4. 独立 `external-dns-public` 只读取带公网标签的 DNSEndpoint，用 Cloudflare DNS-only 发布，TTL 120，TXT owner `yihao-public`，前缀 `_external-dns-public.`。排除 k8s.yhzone.top。
5. 服务删除、Pod 迁移、节点失效或地址授权撤销时更新/清理受管记录。API 查询失败时不基于不完整列表清理记录。

已部署的入口标签不会因 IPv6 授权撤销而立即移除，以保留 DNS 缓存期间的跨节点转发和旧服务。要退役入口节点，先撤销 DNS 授权并等待缓存，再由管理员移除 `networking.yhzone.top/public-gateway` 标签；ali-sas 是固定 IPv4 入口，变更需同步修改控制器配置。

控制器只访问 Kubernetes API，不持有 Cloudflare Secret。公网 ExternalDNS 与内网 ExternalDNS 共用已有凭据 Secret，但 DNS source、域名范围与所有权相互隔离。证书由 cert-manager 使用原 Cloudflare DNS-01 签发；不需要开放 HTTP 80。

控制器及两层入口使用固定版本的上游镜像，避免循环依赖 Harbor。ali-sas 的公网 Pod 请求 64 MiB，基础镜像已预置到 `/var/lib/rancher/k3s/agent/images/public-edge.tar`，升级时须同步版本/镜像；节点其余可调度内存约 83 MiB。控制器固定在首节点。

## 验证与限制

2026-09-24 已验证：

- 八项控制逻辑测试，包含无资源、禁用、非法地址、无 Ready 后端、节点迁移、域名隔离等。
- 删除/恢复手工 IPv6 资源，实际 Cloudflare AAAA 随之撤销/恢复；A 保留。
- 测试 Pod 从首节点迁至 ali-sas，AAAA 自动撤销，IPv4 访问仍正常。
- 公网 IPv4 101.37.69.162:20443 可访问新服务，旧 keys 服务经两节点 SNI 转发保持 HTTPS 正常；内网域名在公网端口被拒绝。
- 本机对首节点全球 IPv6 地址的 HTTPS 访问通过，AAAA 目标正确；尚未从独立外部 IPv6 网络验证上游入站连通性。
- 两个节点通过内网 Harbor 前缀拉取镜像，并使用新的公网认证 realm 成功。

DNS 不是即时故障切换，TTL/客户端缓存及地址变更可能延迟；IPv6/IPv4 连接选择由客户端决定。公网入口与控制平面仍不是跨故障域高可用。

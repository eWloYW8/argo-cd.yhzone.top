# Traefik Ingress

Helm Chart 41.6.0 / Traefik v3.7.13，由 Argo CD 管理。只启用标准 Kubernetes Ingress provider，IngressClass 为 `traefik`，不使用 IngressRoute 或手写路由配置。

入口使用 hostNetwork，只绑定首节点 EasyTier `10.1.2.4:443`；健康检查绑定 `127.0.0.1:18080`，Dashboard 关闭。不创建 LoadBalancer Service，不依赖 K3s 内置 Traefik 或 ServiceLB。当前固定首节点、单副本，升级采用 Recreate，可能短暂中断。

该 PVE LXC 使用 UID 0 + NET_BIND_SERVICE 绑定低端口，其余 capabilities 移除，禁止提权、根文件系统只读。为允许 Harbor 大镜像上传，HTTPS 入口不设置整体请求读取超时。后续公网入口接入时应重新评估超时及流量限制。

## 新增服务

将 `networking.k8s.io/v1` Ingress 放在服务自己的 `resources/` 中并加入 Kustomize：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-cloudflare
    dns.yhzone.top/managed: "true"
    external-dns.kubernetes.io/target: 10.1.2.4
    external-dns.kubernetes.io/ttl: "300"
    external-dns.kubernetes.io/cloudflare-proxied: "false"
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
spec:
  ingressClassName: traefik
  tls:
  - hosts: [example.k8s.yhzone.top]
    secretName: example-ingress-tls
  rules:
  - host: example.k8s.yhzone.top
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: example
            port:
              number: 80
```

Ingress、后端 Service 和 TLS Secret 位于同一个 namespace。cert-manager 根据 Ingress 自动创建每服务证书并使用 Cloudflare DNS-01 签发、续期；Traefik 监听 Secret 变化自动加载。ExternalDNS 从 Ingress 自动管理域名，无需再给后端 Service 添加 DNS 注解。

只有 HTTPS 443 入口，没有 HTTP 80 重定向。公网 20443 尚未接入；当前域名及 Harbor externalURL 保持不变。Argo CD CLI 经此 HTTP 后端入口使用 `--grpc-web`。

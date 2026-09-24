# Public ExternalDNS

Chart 1.22.0 / ExternalDNS 0.22.0，namespace external-dns，复用该 namespace 的 Cloudflare API Secret。

只监听带 `networking.yhzone.top/dns-scope=public` 标签的 DNSEndpoint；允许 yhzone.top、排除 k8s.yhzone.top。TXT owner `yihao-public`、前缀 `_external-dns-public.`，sync 策略会清理撤销的受管 A/AAAA。

DNS 资源由 public-network 控制器根据明确公开的 Ingress 和手工 NodePublicIPv6 资源生成，详见 [公网入口](../public-network/README.md)。禁止把该控制器改为无筛选监听全部 Ingress，避免发布内网服务或接管旧 FRP/Caddy 的 DNS。

# EasyTier 本地启动配置

两个 Kubernetes 节点的 EasyTier 通过 Web 服务管理。Web 服务迁入集群后，必须具备独立于集群的本地组网配置，避免重启时先等 Web、Web 又先等集群网络的循环依赖。

已在 `yihao-pve-debian` 和 `ali-sas`：

- 从运行中的 `easytier-cli -o json node` 导出 `config` TOML，核对实例 ID 和原 IPv4。
- 保存至 `/etc/easytier/config.d/<原实例ID>.toml`，目录 0700，文件 0600。配置含网络密钥，不进入 Git。
- 将本目录的 drop-in 安装至 `/etc/systemd/system/easytier.service.d/20-local-config-cache.conf`，执行 daemon-reload。

`ET_CONFIG_DIR` 对应原程序的 `--config-dir`：启动时加载本地 TOML，运行时保存接收到的配置。原 `-w` 服务端连接参数保持不变。迁移中不重启宿主机 EasyTier；设置下次启动生效，当前保存的是迁移时的运行配置快照。尚未执行整机重启验证。

恢复节点时，必须先从受限备份恢复对应节点的 TOML，再启用此 drop-in。不能把另一节点配置复制过来，也不能重新生成不同实例 ID。若配置发生变更且尚未重启启用自动保存，应重新导出当前运行配置，更新对应 TOML。

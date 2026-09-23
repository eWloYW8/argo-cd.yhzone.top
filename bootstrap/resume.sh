#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
for pair in vm.overcommit_memory=1 kernel.panic=10 kernel.panic_on_oops=1; do
  key=${pair%=*}; expected=${pair#*=}
  actual=$(sudo /usr/sbin/sysctl -n "$key")
  if [[ "$actual" != "$expected" ]]; then
    echo "PVE host prerequisite missing: $key=$actual, expected $expected" >&2
    exit 1
  fi
done
sudo install -m 0600 bootstrap/k3s/config.yaml /etc/rancher/k3s/config.yaml
sudo install -m 0644 bootstrap/k3s/easytier.conf /etc/systemd/system/k3s.service.d/easytier.conf
sudo install -m 0644 bootstrap/k3s/lxc-kmsg.conf /etc/tmpfiles.d/yihao-k3s-kmsg.conf
sudo systemd-tmpfiles --create /etc/tmpfiles.d/yihao-k3s-kmsg.conf
if systemctl is-active --quiet NetworkManager; then
  sudo install -m 0644 bootstrap/k3s/networkmanager.conf /etc/NetworkManager/conf.d/90-yihao-k3s.conf
  sudo nmcli general reload conf
fi
sudo systemctl daemon-reload
sudo systemctl start k3s
k=(kubectl --context yihao)
for i in $(seq 1 60); do
  if "${k[@]}" get node yihao-pve-debian >/dev/null 2>&1; then break; fi
  sleep 2
done
"${k[@]}" wait --for=condition=Ready node/yihao-pve-debian --timeout=180s
"${k[@]}" apply --server-side -k platform/storage
"${k[@]}" create namespace argocd --dry-run=client -o yaml | "${k[@]}" apply -f -
"${k[@]}" apply --server-side -k bootstrap/argocd
"${k[@]}" -n local-path-storage rollout status deployment/local-path-provisioner --timeout=180s
"${k[@]}" -n argocd wait --for=condition=Available deployment --all --timeout=300s
"${k[@]}" -n argocd rollout status statefulset/argocd-application-controller --timeout=300s
printf '%s\n' 'Cluster and Argo CD ready. Push repository and run bootstrap/connect-github.sh.'

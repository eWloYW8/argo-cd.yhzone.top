#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
gh auth status -h github.com
# This uploads only the reviewed repository content. Never add private keys here.
git push -u origin main
key="$HOME/.ssh/yihao-argocd-deploy"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [[ ! -f "$key" ]]; then
  ssh-keygen -t ed25519 -N '' -C yihao-argocd-readonly -f "$key"
fi
if ! gh api repos/eWloYW8/argo-cd.yhzone.top/keys --jq '.[].key' | grep -qF "$(cut -d ' ' -f 1,2 "$key.pub")"; then
  gh repo deploy-key add "$key.pub" --repo eWloYW8/argo-cd.yhzone.top --title yihao-argocd-readonly
fi
# Private key goes directly to the cluster, never to logs or Git.
kubectl --context yihao -n argocd create secret generic yihao-git-repository \
  --from-literal=type=git \
  --from-literal=url=ssh://git@ssh.github.com:443/eWloYW8/argo-cd.yhzone.top.git \
  --from-file=sshPrivateKey="$key" --dry-run=client -o json | \
  kubectl --context yihao apply --server-side -f -
kubectl --context yihao -n argocd label secret yihao-git-repository argocd.argoproj.io/secret-type=repository --overwrite
kubectl --context yihao apply -f bootstrap/root.yaml

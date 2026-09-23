#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
gh auth status -h github.com
git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push -u origin main
python3 bootstrap/configure-repository.py
kubectl --context yihao apply -k platform/project
kubectl --context yihao apply -f bootstrap/root.yaml

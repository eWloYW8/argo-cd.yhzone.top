# Repository conventions

- Use Conventional Commits: `feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`, `chore(scope): ...`.
- Every kubectl mutation must explicitly select context `yihao`.
- Never commit credentials, tokens, private keys, rendered Secrets, or kubeconfigs.
- Pin chart/image versions. Deploy application resources through Argo CD.
- Store persistent application data with the `yihao-local` StorageClass.
- Validate changed Kustomize/Helm manifests before pushing.

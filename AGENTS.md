# Repository conventions

- Use Conventional Commits: `feat(scope): ...`, `fix(scope): ...`, `docs(scope): ...`, `chore(scope): ...`.
- Every kubectl mutation must explicitly select context `yihao`.
- Never commit credentials, tokens, private keys, rendered Secrets, or kubeconfigs.
- Pin chart/image versions. Deploy application resources through Argo CD.
- Store persistent application data with the `yihao-local` StorageClass.
- Validate changed Kustomize/Helm manifests before pushing.

## Service layout

- One service, one directory under `services/`, one generated Argo CD Application.
- Each directory has `app.yaml` (name, namespace, ignoreDifferences) and `kustomization.yaml` (the workload entrypoint).
- Use pinned upstream `helmCharts` and full, versioned `values/<chart>-<version>.yaml`; combine supplemental resources with Kustomize.
- Keep resources and service-specific scripts within the same service directory.
- Do not commit downloaded `charts/`; chart caches are ignored.
- `clusters/yihao` contains the root Application and ApplicationSet; ApplicationSet discovers `services/*/app.yaml`.
- `bootstrap/` contains only host/cluster bootstrap configuration.
- Validate using `kubectl kustomize --enable-helm services/<service>` before pushing. Do not print rendered Secrets.
- Never copy credentials or environment-specific networking from reference repositories.

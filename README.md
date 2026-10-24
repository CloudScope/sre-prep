# sre-prep

Interview preparation for a Senior SRE role: SLOs, observability with OpenTelemetry and Prometheus, incident management, Kubernetes, Terraform, and automation.

- `PLAN.md`: the 14-day plan and progress checklist
- `CLAUDE.md`: context for Claude Code sessions in this repo
- `lab/`: local kind cluster setup, Helm values, and sample app configs
- `docs/`: SLO doc, runbooks, postmortem template, and STAR stories (added as we go)

## Lab quick start

Everything is managed by Argo CD from this repo (app of apps in `lab/argocd/`).
Helm is only used once, to bootstrap Argo CD itself.

```bash
kind create cluster --name local-k8s

helm repo add argo https://argoproj.github.io/argo-helm
helm install argocd argo/argo-cd --version 10.11.1 \
  -n argocd --create-namespace -f lab/helm/argocd-values.yaml

kubectl apply -f lab/argocd/root.yaml
```

Root then syncs: Argo CD (self-managed), kube-prometheus-stack, OTel Collector,
podinfo, orders-api, and the orders-api SLO rules. To change anything, edit the
values or manifests here and push.

Argo CD:
```bash
kubectl -n argocd port-forward svc/argocd-server 8080:80   # http://localhost:8080, user admin
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

Grafana:
```bash
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80   # http://localhost:3000, admin / admin (lab only)
```

Jaeger (traces):
```bash
kubectl -n monitoring port-forward svc/jaeger 16686:16686   # http://localhost:16686, service: orders-api
```

Prometheus:
```bash
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
```

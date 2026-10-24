# sre-prep

Interview preparation for a Senior SRE role: SLOs, observability with OpenTelemetry and Prometheus, incident management, Kubernetes, Terraform, and automation.

- `PLAN.md`: the 14-day plan and progress checklist
- `CLAUDE.md`: context for Claude Code sessions in this repo
- `lab/`: local kind cluster setup, Helm values, and sample app configs
- `docs/`: SLO doc, runbooks, postmortem template, and STAR stories (added as we go)

## Lab quick start

```bash
kind create cluster --name local-k8s

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add podinfo https://stefanprodan.github.io/podinfo
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

helm install monitoring prometheus-community/kube-prometheus-stack --version 92.11.0 \
  -n monitoring --create-namespace -f lab/helm/kube-prometheus-stack-values.yaml
helm install podinfo podinfo/podinfo --version 6.15.0 \
  -n demo --create-namespace -f lab/helm/podinfo-values.yaml
helm install otel open-telemetry/opentelemetry-collector --version 0.177.0 \
  -n monitoring -f lab/helm/otel-collector-values.yaml

kubectl apply -k lab/apps/orders-api
lab/slo/apply.sh
```

Grafana:
```bash
kubectl -n monitoring port-forward svc/monitoring-grafana 3000:80   # http://localhost:3000, admin / admin (lab only)
```

Prometheus:
```bash
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
```

# Lab

Local observability lab on kind. Config files are added here as each day's work is completed.

| Day | Component | Status |
|---|---|---|
| 1 | kind cluster | done |
| 1 | kube-prometheus-stack (`monitoring`) | done (chart 92.11.0, `helm/kube-prometheus-stack-values.yaml`) |
| 1 | podinfo sample app (`demo`) | done (chart 6.15.0, `helm/podinfo-values.yaml`) |
| 2 | OpenTelemetry Collector (`monitoring`) | done (chart 0.177.0, `helm/otel-collector-values.yaml`) |
| 2 | Instrumented sample app (OTel SDK) | done (`apps/orders-api`) |

| 3–4 | SLI recording rules and burn-rate alerts | done (`slo/`, see `docs/slo.md`) |

## Telemetry flow

```
app (OTel SDK) --OTLP--> otel-opentelemetry-collector.monitoring.svc:4317 (gRPC) / :4318 (HTTP)
   metrics -> prometheus exporter :8889 -> ServiceMonitor -> Prometheus
   traces  -> debug exporter (collector logs) until a trace backend is added
   logs    -> debug exporter
collector self-metrics (otelcol_*) :8888 -> ServiceMonitor -> Prometheus
```

App config: `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-opentelemetry-collector.monitoring.svc:4318`

In Prometheus, OTLP metrics carry `exported_job="<service.namespace>/<service.name>"`;
`job` is the collector's own scrape job.

## SLO rules

```bash
promtool test rules lab/slo/orders-api-slo.test.yaml   # unit tests (promtool from the Prometheus release tarball)
lab/slo/render.sh                                      # regenerate lab/slo/k8s/orders-api-slo.yaml; commit it
lab/slo/render.sh --check                              # fail if the committed PrometheusRule is stale
```

## GitOps (Argo CD)

`lab/argocd/root.yaml` is applied once; everything else is in `lab/argocd/apps/`.

| Application | Source | Namespace | Project |
|---|---|---|---|
| `argocd` | `argo/argo-cd` 10.11.1 + `helm/argocd-values.yaml` | `argocd` | platform |
| `kube-prometheus-stack` | `prometheus-community/kube-prometheus-stack` 92.11.0 + `helm/kube-prometheus-stack-values.yaml` | `monitoring` | platform |
| `otel-collector` | `open-telemetry/opentelemetry-collector` 0.177.0 + `helm/otel-collector-values.yaml` | `monitoring` | platform |
| `orders-api-slo` | `slo/k8s/` | `monitoring` | platform |
| `podinfo` | `podinfo/podinfo` 6.15.0 + `helm/podinfo-values.yaml` | `demo` | sre-lab |
| `orders-api` | `apps/orders-api/` (kustomize) | `demo` | sre-lab |

Helm charts use multi-source Applications: chart from the Helm repo, values from this
repo via `$values`. Argo CD renders the chart with `helm template` and applies it; there
is no Helm release, so `helm list` stays empty and `helm upgrade` must not be used.

Sync waves: projects (-1), Argo CD and kube-prometheus-stack (0, they bring the CRDs),
then everything else (1). `platform` may create cluster-scoped objects; `sre-lab` may
only create its own Namespace.


### One-time cutover from Helm releases

The lab was first installed with `helm install`. Argo CD adopts those objects in place
because `releaseName` matches the original release, so the rendered names are the same.
After every app is `Synced` and `Healthy`, delete Helm's release records so nobody runs
`helm upgrade` against objects Argo CD now owns. This removes only Helm's bookkeeping
Secrets, not the workloads (`helm uninstall` would delete the workloads):

```bash
kubectl -n argocd get applications              # all Synced / Healthy first
kubectl -n monitoring delete secret -l owner=helm,name=monitoring
kubectl -n monitoring delete secret -l owner=helm,name=otel
kubectl -n demo       delete secret -l owner=helm,name=podinfo
kubectl -n argocd     delete secret -l owner=helm,name=argocd
helm list -A                                    # should be empty
```

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
lab/slo/apply.sh                                       # wraps the rules in a PrometheusRule and applies it
```


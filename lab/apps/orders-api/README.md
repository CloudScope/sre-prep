# orders-api

Small FastAPI service instrumented with the OpenTelemetry Python SDK (1.45.1).
Sends traces and metrics over OTLP/HTTP to the collector in `monitoring`.

## Deploy

```bash
kubectl apply -k lab/apps/orders-api
```

No image build: the code ships in a ConfigMap and an init container installs
`requirements.txt` on `python:3.13.17-slim`. If Docker is available on the kind host,
build from `Dockerfile` and `kind load docker-image` instead.

`orders-loadgen` sends about 5 req/s to `/orders/{id}` so SLIs always have data.

## What it emits

| Signal | Source | Prometheus name |
|---|---|---|
| HTTP server latency histogram | FastAPI instrumentation (stable semconv) | `http_server_request_duration_seconds_{bucket,count,sum}` |
| Orders by outcome | custom counter `orders.processed` | `orders_processed_total{outcome}` |
| Spans | `GET /orders/{order_id}` server span + child `db.lookup_order` | collector debug log (no trace backend yet) |

`/healthz` is excluded from instrumentation so probe traffic stays out of the SLI.

## Failure injection

```bash
kubectl -n demo set env deploy/orders-api ERROR_RATE=0.05         # 5% of /orders return 500
kubectl -n demo set env deploy/orders-api EXTRA_LATENCY_MS=300    # add 300ms per request
kubectl -n demo set env deploy/orders-api ERROR_RATE=0 EXTRA_LATENCY_MS=0
```

## Useful PromQL

Metrics are scraped from the collector, so `job`, `namespace` and `pod` are the collector's.
The app's identity is `exported_job="demo/orders-api"`; its Kubernetes metadata is on `target_info`.

```promql
# Error ratio (availability SLI basis)
sum(rate(http_server_request_duration_seconds_count{exported_job="demo/orders-api",http_response_status_code=~"5.."}[5m]))
/
sum(rate(http_server_request_duration_seconds_count{exported_job="demo/orders-api"}[5m]))

# p99 latency
histogram_quantile(0.99, sum by (le) (rate(http_server_request_duration_seconds_bucket{exported_job="demo/orders-api"}[5m])))

# Errors per app pod, joining k8s metadata from target_info
sum by (k8s_pod_name) (
  rate(http_server_request_duration_seconds_count{exported_job="demo/orders-api",http_response_status_code=~"5.."}[5m])
  * on (exported_job, exported_instance) group_left(k8s_pod_name) target_info
)
```

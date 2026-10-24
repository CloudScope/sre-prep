# inventory-api

Downstream service called by [orders-api](../orders-api) for every order: `GET /inventory/{item_id}`.
Instrumented with the OpenTelemetry Python SDK (1.45.1), exactly like orders-api.

The FastAPI instrumentation reads the incoming W3C `traceparent` header, so its spans
(`GET /inventory/{item_id}` and child `db.check_stock`) join the caller's trace in Jaeger.

| Knob | Effect |
|---|---|
| `ERROR_RATE` | fraction of requests that return 500; orders-api then answers 502 |
| `EXTRA_LATENCY_MS` | added latency, which shows up inside the orders-api trace |

Change them in `k8s/deployment.yaml` and push: Argo CD self-heal reverts `kubectl set env`.

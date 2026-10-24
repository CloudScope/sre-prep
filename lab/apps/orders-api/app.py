"""orders-api: a small FastAPI service instrumented with the OpenTelemetry SDK.

Every order also checks stock in inventory-api. That call carries the W3C
traceparent header, so one request is one trace across both services. If
inventory-api fails, orders-api answers 502 instead of 500, so the trace and
the status code both show which service broke.

Failure injection (env vars, read on every request so they can be changed
with `kubectl set env` without editing code):
  ERROR_RATE       fraction of /orders requests that return 500 (default 0.0)
  EXTRA_LATENCY_MS added latency on /orders, in milliseconds (default 0)

Other settings:
  INVENTORY_URL    base URL of inventory-api (default http://inventory-api:8000)

Exporter settings come from the standard OTEL_* env vars, for example
OTEL_EXPORTER_OTLP_ENDPOINT and OTEL_SERVICE_NAME.
"""

import os
import random
import time

import httpx
from fastapi import FastAPI, HTTPException
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Resource.create() merges OTEL_SERVICE_NAME and OTEL_RESOURCE_ATTRIBUTES.
resource = Resource.create({"service.version": os.getenv("APP_VERSION", "0.1.0")})

tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(tracer_provider)

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter(), export_interval_millis=15000)],
)
metrics.set_meter_provider(meter_provider)

tracer = trace.get_tracer("orders-api")
meter = metrics.get_meter("orders-api")

orders_processed = meter.create_counter(
    "orders.processed", unit="{order}", description="Orders processed, by outcome"
)

# Instrument httpx before creating the client: every outgoing call becomes a
# client span and carries the traceparent header to inventory-api.
HTTPXClientInstrumentor().instrument()
inventory = httpx.Client(base_url=os.getenv("INVENTORY_URL", "http://inventory-api:8000"), timeout=2.0)

app = FastAPI(title="orders-api")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    error_rate = float(os.getenv("ERROR_RATE", "0"))
    extra_latency_ms = int(os.getenv("EXTRA_LATENCY_MS", "0"))

    with tracer.start_as_current_span("db.lookup_order") as span:
        span.set_attribute("order.id", order_id)
        time.sleep(random.uniform(0.005, 0.03) + extra_latency_ms / 1000)

        if random.random() < error_rate:
            orders_processed.add(1, {"outcome": "error"})
            span.set_status(trace.StatusCode.ERROR, "injected failure")
            raise HTTPException(status_code=500, detail="injected failure")

    try:
        inventory.get(f"/inventory/{order_id % 100}").raise_for_status()
    except httpx.HTTPError as exc:
        orders_processed.add(1, {"outcome": "dependency_error"})
        trace.get_current_span().set_status(trace.StatusCode.ERROR, f"inventory-api: {exc}")
        raise HTTPException(status_code=502, detail="inventory-api failed") from exc

    orders_processed.add(1, {"outcome": "ok"})
    return {"order_id": order_id, "status": "shipped"}


# Excluding /healthz keeps probe traffic out of the SLI.
FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz", meter_provider=meter_provider)

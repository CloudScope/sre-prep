"""inventory-api: downstream service called by orders-api, instrumented with the OpenTelemetry SDK.

orders-api calls GET /inventory/{item_id} for every order. The incoming W3C
traceparent header is picked up by the FastAPI instrumentation, so these spans
join the caller's trace.

Failure injection (env vars, read on every request):
  ERROR_RATE       fraction of /inventory requests that return 500 (default 0.0)
  EXTRA_LATENCY_MS added latency on /inventory, in milliseconds (default 0)

Exporter settings come from the standard OTEL_* env vars, for example
OTEL_EXPORTER_OTLP_ENDPOINT and OTEL_SERVICE_NAME.
"""

import os
import random
import time

from fastapi import FastAPI, HTTPException
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
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

tracer = trace.get_tracer("inventory-api")
meter = metrics.get_meter("inventory-api")

stock_checks = meter.create_counter(
    "inventory.stock_checks", unit="{check}", description="Stock checks, by outcome"
)

app = FastAPI(title="inventory-api")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/inventory/{item_id}")
def get_stock(item_id: int):
    error_rate = float(os.getenv("ERROR_RATE", "0"))
    extra_latency_ms = int(os.getenv("EXTRA_LATENCY_MS", "0"))

    with tracer.start_as_current_span("db.check_stock") as span:
        span.set_attribute("inventory.item_id", item_id)
        time.sleep(random.uniform(0.002, 0.015) + extra_latency_ms / 1000)

        if random.random() < error_rate:
            stock_checks.add(1, {"outcome": "error"})
            span.set_status(trace.StatusCode.ERROR, "injected failure")
            raise HTTPException(status_code=500, detail="injected failure")

    stock_checks.add(1, {"outcome": "ok"})
    return {"item_id": item_id, "in_stock": 100 - item_id % 7}


# Excluding /healthz keeps probe traffic out of the SLI.
FastAPIInstrumentor.instrument_app(app, excluded_urls="healthz", meter_provider=meter_provider)

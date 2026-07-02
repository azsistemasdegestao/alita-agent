"""Observability bootstrap (traces/metrics/logs) for the FastAPI `api.py`.

Python equivalent of `frontend/src/instrument.mts`: registers the global
OpenTelemetry providers and instruments FastAPI + httpx before any other
agent module is imported. `setup()` must run before
`from .ecommerce_client import client` in `api.py` — `HTTPXClientInstrumentor`
patches `httpx.AsyncClient` globally, so if the client has already been
imported/created before this runs, tracing for Ecommerce API calls silently
does not apply (no error raised).

Only covers the FastAPI path (`api.py`, used in production/Docker) — the
`adk run`/`adk web` entry points intentionally do not go through this.
"""

import logging
import os

from fastapi import FastAPI, Response
from loki_logger_handler.loki_logger_handler import LokiLoggerHandler
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

SERVICE_NAME_VALUE = os.getenv("OTEL_SERVICE_NAME", "alita-agent")
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://localhost:4317")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")


def setup(app: FastAPI) -> None:
    resource = Resource.create({SERVICE_NAME: SERVICE_NAME_VALUE})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=JAEGER_ENDPOINT, insecure=True))
    )
    trace.set_tracer_provider(tracer_provider)

    FastAPIInstrumentor.instrument_app(app)
    # Global patch of httpx.AsyncClient — covers `ecommerce_client.py` as well
    # as google-adk's own internal spans for its HTTP calls to Gemini.
    HTTPXClientInstrumentor().instrument()

    meter_provider = MeterProvider(resource=resource, metric_readers=[PrometheusMetricReader()])
    metrics.set_meter_provider(meter_provider)

    @app.get("/metrics")
    async def metrics_endpoint() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # LokiLoggerHandler POSTs directly to the given URL without appending the
    # push path itself — it must be the push endpoint, not just LOKI_URL's host:port.
    loki_handler = LokiLoggerHandler(
        url=f"{LOKI_URL}/loki/api/v1/push", labels={"app": "alita-agent"}
    )
    root_logger.addHandler(loki_handler)


def shutdown() -> None:
    tracer_provider = trace.get_tracer_provider()
    if isinstance(tracer_provider, TracerProvider):
        tracer_provider.force_flush()
        tracer_provider.shutdown()

    meter_provider = metrics.get_meter_provider()
    if isinstance(meter_provider, MeterProvider):
        meter_provider.shutdown()

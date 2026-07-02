"""Bootstrap de observabilidade (traces/metrics/logs) para o FastAPI `api.py`.

Equivalente Python do `frontend/src/instrument.mts`: registra os providers
globais do OpenTelemetry e instrumenta FastAPI + httpx antes de qualquer
outro módulo do agente ser importado. `setup()` precisa rodar antes de
`from .ecommerce_client import client` em `api.py` — `HTTPXClientInstrumentor`
faz patch global em `httpx.AsyncClient`, então se o client já tiver sido
importado/criado antes disso, o tracing das chamadas à Ecommerce API não é
aplicado (falha silenciosa, sem erro).

Cobre apenas o caminho FastAPI (`api.py`, usado em produção/Docker) — os
entry points `adk run`/`adk web` não passam por aqui, propositalmente.
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
    # Patch global do httpx.AsyncClient — cobre `ecommerce_client.py` e também
    # os spans internos do google-adk que fazem chamadas HTTP ao Gemini.
    HTTPXClientInstrumentor().instrument()

    meter_provider = MeterProvider(resource=resource, metric_readers=[PrometheusMetricReader()])
    metrics.set_meter_provider(meter_provider)

    @app.get("/metrics")
    async def metrics_endpoint() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # LokiLoggerHandler faz POST direto na URL informada, sem completar o path
    # — precisa ser o endpoint de push, não só o host:porta do LOKI_URL.
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

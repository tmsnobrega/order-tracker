"""Record request outcomes without putting order or customer data in telemetry."""

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter


def configure():
    mode = os.getenv("OTEL_EXPORTER_MODE", "none")
    if mode == "none":
        return
    resource = Resource.create({
        "service.name": "order-tracker",
        "service.version": os.getenv("APP_VERSION", "hw04-instrumented"),
    })
    if mode == "console":
        spans, metric_exporter, logs = ConsoleSpanExporter(), ConsoleMetricExporter(), ConsoleLogExporter()
    elif mode == "otlp":
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318").rstrip("/")
        spans = OTLPSpanExporter(endpoint=endpoint + "/v1/traces")
        metric_exporter = OTLPMetricExporter(endpoint=endpoint + "/v1/metrics")
        logs = OTLPLogExporter(endpoint=endpoint + "/v1/logs")
    else:
        raise ValueError("OTEL_EXPORTER_MODE must be none, console, or otlp")
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(spans))
    trace.set_tracer_provider(trace_provider)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[
        PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
    ]))
    log_provider = LoggerProvider(resource=resource)
    log_provider.add_log_record_processor(BatchLogRecordProcessor(logs))
    logger = logging.getLogger("order-tracker.requests")
    logger.addHandler(LoggingHandler(logger_provider=log_provider))
    logger.setLevel(logging.INFO)
    logger.propagate = False


configure()
counter = metrics.get_meter("order-tracker").create_counter("http.server.requests")
logger = logging.getLogger("order-tracker.requests")
tracer = trace.get_tracer("order-tracker")


class TelemetryMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # A route template keeps IDs out of labels and limits metric cardinality.
        path = scope["path"]
        route = "/api/orders/{order_id}" if path.startswith("/api/orders/") else path
        if route not in {"/", "/healthz", "/api/orders", "/api/orders/{order_id}"}:
            route = "unmatched"
        status = 500
        attrs = {"http.route": route, "http.request.method": scope["method"]}
        with tracer.start_as_current_span(f"{scope['method']} {route}", kind=trace.SpanKind.SERVER) as span:
            async def tracked_send(message):
                nonlocal status
                if message["type"] == "http.response.start":
                    status = message["status"]
                await send(message)

            try:
                await self.app(scope, receive, tracked_send)
            except Exception as error:
                span.record_exception(error)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                raise
            finally:
                attrs["http.response.status_code"] = status
                span.set_attributes(attrs)
                counter.add(1, attrs)
                logger.log(logging.ERROR if status >= 500 else logging.INFO,
                           "request finished", extra=attrs)

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from sqlalchemy import Engine

from the_finance_genie.utils.telemetry.exporters import LazyBatchSpanProcessor
from the_finance_genie.utils.telemetry.instrumentors import Instrumentor
from the_finance_genie.env import OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT


def setup(app: FastAPI, db_engine: Engine):
    # set up trace
    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create(attributes={SERVICE_NAME: OTEL_SERVICE_NAME})
        )
    )
    # otlp export
    exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)
    trace.get_tracer_provider().add_span_processor(LazyBatchSpanProcessor(exporter))
    Instrumentor(app=app, db_engine=db_engine).instrument()

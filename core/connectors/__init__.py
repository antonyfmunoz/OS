"""Real Data Connectors — ingest external metrics into the reality loop."""

from core.connectors.base import (
    Connector,
    CsvFileAdapter,
    JsonFileAdapter,
    LogFileAdapter,
    RealSignal,
    WebhookPayloadAdapter,
    aggregate_signals,
    dict_to_signal,
)
from core.connectors.content import ContentConnector
from core.connectors.crm import CrmConnector
from core.connectors.email import EmailConnector

__all__ = [
    "Connector",
    "RealSignal",
    "JsonFileAdapter",
    "CsvFileAdapter",
    "LogFileAdapter",
    "WebhookPayloadAdapter",
    "dict_to_signal",
    "aggregate_signals",
    "EmailConnector",
    "ContentConnector",
    "CrmConnector",
]

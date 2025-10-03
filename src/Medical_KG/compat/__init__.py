"""Typed facades for optional third-party dependencies."""

from .httpx import (
    AsyncClientProtocol,
    ClientProtocol,
    HTTPError,
    ResponseProtocol,
    create_async_client,
    create_client,
)
from .locust import HttpUserProtocol, TaskDecorator, WaitTimeFactory, load_locust
from .prometheus import Counter, CounterLike, Gauge, GaugeLike, Histogram, HistogramLike
from .spacy import DocProtocol, PipelineProtocol, SpanProtocol, load_pipeline
from .tiktoken import EncodingProtocol, load_encoding
from .torch import CudaProtocol, TorchProtocol, load_torch

__all__ = [
    "AsyncClientProtocol",
    "ClientProtocol",
    "HTTPError",
    "ResponseProtocol",
    "create_async_client",
    "create_client",
    "Counter",
    "CounterLike",
    "Gauge",
    "GaugeLike",
    "Histogram",
    "HistogramLike",
    "HttpUserProtocol",
    "TaskDecorator",
    "WaitTimeFactory",
    "load_locust",
    "DocProtocol",
    "PipelineProtocol",
    "SpanProtocol",
    "load_pipeline",
    "EncodingProtocol",
    "load_encoding",
    "CudaProtocol",
    "TorchProtocol",
    "load_torch",
]

from __future__ import annotations

from collections.abc import Sequence

import pytest

from Medical_KG.embeddings.qwen import QwenEmbeddingClient
from Medical_KG.embeddings.splade import SPLADEExpander


def test_qwen_embeddings_are_deterministic() -> None:
    client = QwenEmbeddingClient(dimension=8, batch_size=4)
    first = client.embed(["hello world"])[0]
    second = client.embed(["hello world"])[0]
    assert pytest.approx(first) == second
    norm = sum(value * value for value in first) ** 0.5
    assert pytest.approx(norm, rel=1e-6) == 1.0


def test_qwen_client_http_and_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    class DummyResponse:
        def __init__(self, *, ok: bool) -> None:
            self._ok = ok

        def raise_for_status(self) -> None:
            if not self._ok:
                raise RuntimeError("http error")

        def json(self) -> dict[str, object]:
            return {"data": [{"embedding": [0.1, 0.2]}]}

    class DummyClient:
        def __init__(self) -> None:
            self.closed = False

        def post(self, url: str, json: dict[str, object]) -> DummyResponse:
            calls.append(1)
            if len(calls) == 1:
                return DummyResponse(ok=False)
            return DummyResponse(ok=True)

        def close(self) -> None:
            self.closed = True

    client_instance = DummyClient()

    def factory() -> DummyClient:
        return client_instance

    sleeps: list[float] = []

    client = QwenEmbeddingClient(
        dimension=2,
        batch_size=8,
        api_url="http://fake",
        http_client_factory=factory,
        max_retries=2,
        sleep=lambda value: sleeps.append(value),
    )
    vectors = client.embed(["text"])
    assert vectors == [[0.1, 0.2]]
    assert len(calls) == 2
    assert sleeps  # retry occurred


def test_qwen_client_transport_override() -> None:
    def transport(texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]

    client = QwenEmbeddingClient(dimension=1, transport=transport)
    vectors = client.embed(["alpha", "beta"])
    assert vectors == [[5.0], [4.0]]


def test_splade_expander_filters_terms() -> None:
    expander = SPLADEExpander(top_k=2, min_weight=0.0, batch_size=2)
    expansions = expander.expand(["Alpha beta beta", ""])
    assert "beta" in expansions[0]
    assert expansions[1] == {}

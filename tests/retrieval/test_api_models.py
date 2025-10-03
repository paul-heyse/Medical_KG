from __future__ import annotations

from Medical_KG.retrieval.api import RetrieveQuery


def test_retrieve_query_to_request_defaults() -> None:
    payload = RetrieveQuery(query="pembrolizumab")
    request = payload.to_request()
    assert request.query == "pembrolizumab"
    assert request.top_k == 20
    assert request.filters == {}
    assert request.from_ == 0
    assert request.explain is False


def test_retrieve_query_with_filters_and_aliases() -> None:
    payload = RetrieveQuery(
        query="pembrolizumab",
        filters={"facet_type": "drug"},
        topK=50,
        **{"from": 10},
        intent="lookup",
        rerank_enabled=True,
        explain=True,
    )
    request = payload.to_request()
    assert request.top_k == 50
    assert request.from_ == 10
    assert request.filters == {"facet_type": "drug"}
    assert request.intent == "lookup"
    assert request.rerank_enabled is True
    assert request.explain is True


def test_retrieve_query_defaults_filters_to_empty_dict() -> None:
    payload = RetrieveQuery(query="term")
    assert payload.filters == {}

from __future__ import annotations

from dataclasses import dataclass


from Medical_KG.entity_linking.ner import Mention, NerPipeline


@dataclass
class _StubSpan:
    text: str
    start_char: int
    end_char: int
    label_: str


@dataclass
class _StubDoc:
    ents: list[_StubSpan]


def test_ner_pipeline_returns_mentions(monkeypatch) -> None:
    def _fake_loader(model: str):
        def _call(text: str) -> _StubDoc:
            return _StubDoc([_StubSpan(text="myocardial infarction", start_char=3, end_char=25, label_="disease")])

        return _call

    monkeypatch.setattr("Medical_KG.entity_linking.ner.load_pipeline", _fake_loader)

    pipeline = NerPipeline(model="stub")
    mentions = pipeline("DX: myocardial infarction")

    assert mentions == [Mention(text="myocardial infarction", start=3, end=25, label="disease")]


def test_ner_pipeline_returns_empty_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("Medical_KG.entity_linking.ner.load_pipeline", lambda model: None)

    pipeline = NerPipeline(model="missing")
    assert pipeline("text") == []


def test_ner_pipeline_prefers_longest_overlap(monkeypatch) -> None:
    def _fake_loader(model: str):
        def _call(text: str) -> _StubDoc:
            return _StubDoc(
                [
                    _StubSpan(text="MI", start_char=5, end_char=7, label_="disease"),
                    _StubSpan(text="myocardial infarction", start_char=5, end_char=25, label_="disease"),
                ]
            )

        return _call

    monkeypatch.setattr("Medical_KG.entity_linking.ner.load_pipeline", _fake_loader)
    pipeline = NerPipeline(model="stub")
    mentions = pipeline("dx: MI myocardial infarction")

    assert mentions == [
        Mention(text="MI", start=5, end=7, label="disease"),
        Mention(text="myocardial infarction", start=5, end=25, label="disease"),
    ]


def test_ner_pipeline_skips_negated_mentions(monkeypatch) -> None:
    def _fake_loader(model: str):
        def _call(text: str) -> _StubDoc:
            return _StubDoc([_StubSpan(text="cancer", start_char=3, end_char=9, label_="disease")])

        return _call

    monkeypatch.setattr("Medical_KG.entity_linking.ner.load_pipeline", _fake_loader)
    pipeline = NerPipeline(model="stub")
    assert pipeline("no cancer detected") == [
        Mention(text="cancer", start=3, end=9, label="disease")
    ]


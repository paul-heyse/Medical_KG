import pytest

from Medical_KG.pdf.postprocess import TextBlock
from Medical_KG.pdf.qa import QaGateError, QaGates


def make_blocks() -> list[TextBlock]:
    return [
        TextBlock(page=1, y=100, text="Introduction"),
        TextBlock(page=1, y=200, text="Methods"),
        TextBlock(page=2, y=50, text="Results"),
    ]


def test_qa_gates_success() -> None:
    gates = QaGates(reading_order_threshold=0.5, ocr_threshold=0.5)

    metrics = gates.evaluate(blocks=make_blocks(), confidences=[0.9, 0.8], tables=[])

    assert metrics.reading_order_score == pytest.approx(1.0)
    assert metrics.ocr_confidence_mean == pytest.approx(0.85)
    assert metrics.header_footer_suppressed == 0


def test_qa_gates_rejects_bad_reading_order() -> None:
    gates = QaGates(reading_order_threshold=0.9)
    blocks = [
        TextBlock(page=1, y=200, text="Methods"),
        TextBlock(page=1, y=100, text="Introduction"),
    ]

    with pytest.raises(QaGateError):
        gates.evaluate(blocks=blocks, confidences=[1.0], tables=[])


def test_qa_gates_rejects_poor_ocr_and_tables() -> None:
    gates = QaGates(ocr_threshold=0.9)
    blocks = make_blocks()
    tables = [{"rows": [["A"]]}]  # invalid: single-column table

    with pytest.raises(QaGateError):
        gates.evaluate(blocks=blocks, confidences=[0.2, 0.3], tables=tables)

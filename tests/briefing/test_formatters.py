from __future__ import annotations

import io
import json
import zipfile

import pytest

from Medical_KG.briefing.formatters import BriefingFormatter

_pdfminer = pytest.importorskip("pdfminer.high_level")
extract_text = _pdfminer.extract_text


@pytest.fixture
def formatter() -> BriefingFormatter:
    return BriefingFormatter()


@pytest.fixture
def payload() -> dict[str, object]:
    items = [
        {
            "summary": "Response rate improved",
            "citations": [
                {"doc_id": "doc-1", "quote": "Improved"},
                {"doc_id": "doc-2", "quote": "Stable"},
            ],
        },
        {
            "description": "Grade 3 toxicities were rare",
            "citations": [],
        },
    ]
    items.extend({"summary": f"Detail {index}", "citations": []} for index in range(40))

    return {
        "topic": "Lung Cancer",
        "sections": [
            {
                "title": "Summary",
                "items": items,
            },
        ],
        "bibliography": [
            {"doc_id": "doc-1", "citation_count": 2},
            {"doc_id": "doc-2", "citation_count": 1},
        ],
    }


def test_to_json_and_markdown(formatter: BriefingFormatter, payload: dict[str, object]) -> None:
    json_output = formatter.to_json(payload)
    markdown_output = formatter.to_markdown(payload)

    as_dict = json.loads(json_output)
    assert as_dict["topic"] == "Lung Cancer"

    assert "# Topic Dossier: Lung Cancer" in markdown_output
    assert "- Response rate improved" in markdown_output
    assert "Citations: doc-1, doc-2" in markdown_output
    assert "## Bibliography" in markdown_output


def test_to_html_allows_custom_stylesheet(payload: dict[str, object]) -> None:
    formatter = BriefingFormatter(stylesheet="body { background: black; }")
    html_output = formatter.to_html(payload)

    assert "background: black" in html_output
    assert "<section><h2>Summary</h2><ul>" in html_output
    assert "doc-1" in html_output


def test_to_pdf_creates_textual_canvas(
    formatter: BriefingFormatter, payload: dict[str, object]
) -> None:
    pdf_bytes = formatter.to_pdf(payload)

    # Verify key PDF markers rather than raw text contents
    assert pdf_bytes.startswith(b"%PDF-")
    extracted = extract_text(io.BytesIO(pdf_bytes))
    assert "Topic Dossier: Lung Cancer" in extracted


def test_to_docx_converts_markdown(
    formatter: BriefingFormatter, payload: dict[str, object]
) -> None:
    docx_bytes = formatter.to_docx(payload)

    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as archive:
        namelist = set(archive.namelist())
        assert "word/document.xml" in namelist
        xml_payload = archive.read("word/document.xml").decode("utf-8")

    assert "Response rate improved" in xml_payload
    assert "Topic Dossier: Lung Cancer" in xml_payload


@pytest.fixture
def partial_payload() -> dict[str, object]:
    return {
        "sections": [
            {
                "items": [
                    {
                        "description": "Observation",  # summary missing
                        "citations": [
                            {"quote": "Lines available without identifier"},
                        ],
                    },
                    {
                        "summary": "Secondary insight",
                        "citations": [
                            {"doc_id": None, "quote": "Missing doc id"},
                        ],
                    },
                ]
            }
        ],
        "bibliography": [
            {"citation_count": "3"},
            {"doc_id": "doc-2"},
        ],
    }


def test_to_markdown_handles_partial_payload(
    formatter: BriefingFormatter, partial_payload: dict[str, object]
) -> None:
    markdown_output = formatter.to_markdown(partial_payload)

    assert "# Topic Dossier: Untitled Briefing" in markdown_output
    assert "## Untitled Section" in markdown_output
    assert "- Observation" in markdown_output
    assert "Citations: Unknown" in markdown_output
    assert "- Unknown (3 references)" in markdown_output


def test_to_html_handles_partial_payload(
    formatter: BriefingFormatter, partial_payload: dict[str, object]
) -> None:
    html_output = formatter.to_html(partial_payload)

    assert "Topic Dossier: Untitled Briefing" in html_output
    assert "<h2>Untitled Section</h2>" in html_output
    assert "[Unknown]" in html_output
    assert "(3 refs)" in html_output


def test_to_pdf_handles_partial_payload(
    formatter: BriefingFormatter, partial_payload: dict[str, object]
) -> None:
    pdf_bytes = formatter.to_pdf(partial_payload)

    assert pdf_bytes.startswith(b"%PDF-")
    text = extract_text(io.BytesIO(pdf_bytes))
    assert "Topic Dossier: Untitled Briefing" in text
    assert "Untitled Section" in text

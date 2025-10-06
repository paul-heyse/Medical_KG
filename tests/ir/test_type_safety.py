import textwrap
from pathlib import Path

from mypy import api as mypy_api


def test_mypy_rejects_untyped_ir_payload(tmp_path: Path) -> None:
    snippet = textwrap.dedent(
        """
        from Medical_KG.ir.builder import IrBuilder

        builder = IrBuilder()
        builder.build(
            doc_id="doc",
            source="pubmed",
            uri="https://example.org",
            text="",
            raw={"pmid": "123"},
        )
        """
    )
    target = tmp_path / "snippet.py"
    target.write_text(snippet)
    stdout, stderr, exit_status = mypy_api.run([str(target)])
    assert exit_status != 0, stdout
    assert "Argument \"raw\"" in stdout

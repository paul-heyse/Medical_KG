from Medical_KG.pdf.postprocess import (
    HeaderFooterSuppressor,
    HyphenationRepair,
    SectionLabeler,
    TextBlock,
    TwoColumnReflow,
)


def test_two_column_reflow_detects_and_orders_blocks() -> None:
    blocks = [
        TextBlock(page=1, y=45, text="Intro"),
        TextBlock(page=1, y=65, text="Background"),
        TextBlock(page=1, y=85, text="Discussion"),
        TextBlock(page=1, y=95, text="Conclusion"),
        TextBlock(page=1, y=355, text="Methods"),
        TextBlock(page=1, y=375, text="Results"),
    ]
    reflow = TwoColumnReflow()

    assert reflow.detect_columns(blocks)

    ordered = reflow.reflow(blocks)
    texts = [block.text for block in ordered]

    assert texts == [
        "Intro",
        "Background",
        "Discussion",
        "Conclusion",
        "Methods",
        "Results",
    ]


def test_header_footer_suppressor_removes_repeated_text() -> None:
    suppressor = HeaderFooterSuppressor()
    blocks = [
        TextBlock(page=1, y=20, text="Trial Title"),
        TextBlock(page=1, y=120, text="Introduction paragraph"),
        TextBlock(page=2, y=20, text="Trial Title"),
        TextBlock(page=2, y=130, text="Methods paragraph"),
        TextBlock(page=3, y=20, text="Trial Title"),
        TextBlock(page=3, y=140, text="Results paragraph"),
    ]

    filtered = suppressor.suppress(blocks)

    assert all(block.text != "Trial Title" for block in filtered)
    assert [block.text for block in filtered] == [
        "Introduction paragraph",
        "Methods paragraph",
        "Results paragraph",
    ]


def test_hyphenation_repair_and_section_labeling() -> None:
    repair = HyphenationRepair()
    labeler = SectionLabeler()
    blocks = [
        TextBlock(page=1, y=100, text="Introduction"),
        TextBlock(page=1, y=200, text="Back-" "\nground"),
        TextBlock(page=1, y=300, text="Methods"),
    ]

    repaired = [
        TextBlock(block.page, block.y, repair.repair(block.text)) for block in blocks
    ]
    labeled = labeler.label(repaired)

    assert repaired[1].text == "Background"
    assert [block.label for block in labeled] == [
        "introduction",
        "introduction",
        "methods",
    ]

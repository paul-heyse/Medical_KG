from __future__ import annotations

from io import BytesIO
from typing import Iterable, Sequence, cast


class Canvas:
    """Lightweight PDF canvas that emits valid PDF streams."""

    def __init__(self, buffer: BytesIO, pagesize: Sequence[float]) -> None:
        self._buffer = buffer
        self._pagesize = pagesize
        self._closed = False
        self._current_font = ("Helvetica", 12.0)
        self._fonts: set[str] = {"Helvetica"}
        self._commands: list[tuple[str, object, object, object]] = []
        self._pages: list[list[tuple[str, object, object, object]]] = []

    def setFont(self, name: str, size: float) -> None:
        self._current_font = (name, float(size))
        self._fonts.add(name)
        self._commands.append(("font", name, float(size), None))

    def drawString(self, x: float, y: float, text: str) -> None:
        self._commands.append(("text", float(x), float(y), str(text)))

    def showPage(self) -> None:
        self._pages.append(list(self._commands))
        self._commands = []
        self._current_font = ("Helvetica", 12.0)

    def save(self) -> None:
        if self._closed:
            return
        if self._commands:
            self.showPage()
        payload = _build_pdf(self._pages, self._fonts, self._pagesize)
        self._buffer.write(payload)
        self._closed = True


def _build_pdf(
    pages: Iterable[list[tuple[str, object, object, object]]],
    fonts: set[str],
    pagesize: Sequence[float],
) -> bytes:
    width, height = float(pagesize[0]), float(pagesize[1])
    object_bodies: list[bytes] = []
    initialised: set[int] = set()

    def reserve_object() -> int:
        object_bodies.append(b"")
        return len(object_bodies)

    def set_object(obj_num: int, body: bytes) -> None:
        object_bodies[obj_num - 1] = body
        initialised.add(obj_num)

    font_aliases: dict[str, tuple[str, int]] = {}
    if not fonts:
        fonts.add("Helvetica")
    for index, font_name in enumerate(sorted(fonts), start=1):
        alias = f"F{index}"
        obj_num = reserve_object()
        font_body = f"<< /Type /Font /Subtype /Type1 /BaseFont /{font_name} >>".encode("utf-8")
        set_object(obj_num, font_body)
        font_aliases[font_name] = (alias, obj_num)

    resource_entries = " ".join(
        f"/{alias} {obj_num} 0 R"
        for alias, obj_num in (font_aliases[name] for name in sorted(font_aliases))
    )
    resources_text = f"<< /Font << {resource_entries} >> >>"
    page_command_lists = list(pages)
    content_obj_nums: list[int] = []
    for command_list in page_command_lists:
        stream_lines: list[str] = []
        current_font = ("Helvetica", 12.0)
        for cmd, arg1, arg2, arg3 in command_list:
            if cmd == "font":
                current_font = (str(arg1), float(cast(float, arg2)))
                continue
            if cmd != "text":
                continue
            font_name, font_size = current_font
            alias, _ = font_aliases.get(font_name, font_aliases[next(iter(font_aliases))])
            x = float(cast(float, arg1))
            y = float(cast(float, arg2))
            text = str(arg3).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_lines.append(f"BT /{alias} {font_size:.2f} Tf {x:.2f} {y:.2f} Td ({text}) Tj ET")
        stream_bytes = "\n".join(stream_lines).encode("utf-8")
        obj_num = reserve_object()
        content = (
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("utf-8")
            + stream_bytes
            + b"\nendstream"
        )
        set_object(obj_num, content)
        content_obj_nums.append(obj_num)

    page_obj_nums = [reserve_object() for _ in page_command_lists]
    pages_obj_num = reserve_object()
    catalog_obj_num = reserve_object()

    for obj_num, content_num in zip(page_obj_nums, content_obj_nums):
        body = (
            f"<< /Type /Page /Parent {pages_obj_num} 0 R /MediaBox [0 0 {width:.2f} {height:.2f}] "
            f"/Resources {resources_text} /Contents {content_num} 0 R >>"
        ).encode("utf-8")
        set_object(obj_num, body)

    kids = " ".join(f"{num} 0 R" for num in page_obj_nums)
    pages_body = f"<< /Type /Pages /Count {len(page_obj_nums)} /Kids [{kids}] >>".encode("utf-8")
    set_object(pages_obj_num, pages_body)

    catalog_body = f"<< /Type /Catalog /Pages {pages_obj_num} 0 R >>".encode("utf-8")
    set_object(catalog_obj_num, catalog_body)

    pdf = bytearray(b"%PDF-1.3\n")
    offsets: list[int] = []
    for index, body in enumerate(object_bodies, start=1):
        if index not in initialised:
            raise RuntimeError("PDF object was not initialised")
        body_bytes = body
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("utf-8"))
        pdf.extend(body_bytes)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(object_bodies) + 1}\n".encode("utf-8"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
    pdf.extend(b"trailer\n")
    pdf.extend(
        f"<< /Size {len(object_bodies) + 1} /Root {catalog_obj_num} 0 R >>\n".encode("utf-8")
    )
    pdf.extend(b"startxref\n")
    pdf.extend(f"{xref_offset}\n%%EOF\n".encode("utf-8"))
    return bytes(pdf)


__all__ = ["Canvas"]

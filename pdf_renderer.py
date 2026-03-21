from __future__ import annotations

from typing import Iterable

from resume_service import ResumeSection, TailoredResume

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT_MARGIN = 54
TOP_MARGIN = 54
BOTTOM_MARGIN = 54
LINE_HEIGHT = 14
FONT_SIZE = 11
MAX_CHARS_PER_LINE = 92



def _escape_pdf_text(value: str) -> str:
    return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')



def _wrap_line(text: str, width: int = MAX_CHARS_PER_LINE) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines



def _resume_lines(resume: TailoredResume) -> list[str]:
    lines: list[str] = []
    lines.extend(_wrap_line(resume.name or "Tailored Resume", 80))
    if resume.headline:
        lines.extend(_wrap_line(resume.headline, 80))
    if resume.contact:
        lines.extend(_wrap_line(" | ".join(resume.contact), 100))
    lines.append("")

    def section(title: str):
        lines.append(title.upper())

    if resume.summary:
        section("Professional Summary")
        for item in resume.summary:
            lines.extend(_wrap_line(f"- {item}"))
        lines.append("")

    if resume.skills:
        section("Core Skills")
        lines.extend(_wrap_line(", ".join(resume.skills)))
        lines.append("")

    if resume.experience:
        section("Professional Experience")
        for entry in resume.experience:
            header = " — ".join(part for part in [entry.role, entry.company] if part)
            if header:
                lines.extend(_wrap_line(header, 88))
            if entry.dates:
                lines.append(entry.dates)
            for bullet in entry.bullets:
                lines.extend(_wrap_line(f"- {bullet}"))
            lines.append("")

    def custom_sections(title: str, sections: list[ResumeSection]):
        if not sections:
            return
        section(title)
        for block in sections:
            if block.heading:
                lines.extend(_wrap_line(block.heading, 88))
            for item in block.items:
                lines.extend(_wrap_line(f"- {item}"))
            lines.append("")

    custom_sections("Projects", resume.projects)
    custom_sections("Education", resume.education)

    if resume.tailoring_notes:
        section("Tailoring Notes")
        for item in resume.tailoring_notes:
            lines.extend(_wrap_line(f"- {item}"))

    while lines and lines[-1] == "":
        lines.pop()
    return lines



def _chunk_lines(lines: Iterable[str], per_page: int) -> list[list[str]]:
    page_lines: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if len(current) >= per_page:
            page_lines.append(current)
            current = []
    if current:
        page_lines.append(current)
    return page_lines or [[""]]



def _content_stream(page_lines: list[str]) -> bytes:
    start_y = PAGE_HEIGHT - TOP_MARGIN
    commands = ["BT", f"/F1 {FONT_SIZE} Tf", f"1 0 0 1 {LEFT_MARGIN} {start_y} Tm"]
    for index, line in enumerate(page_lines):
        if index > 0:
            commands.append(f"0 -{LINE_HEIGHT} Td")
        commands.append(f"({_escape_pdf_text(line)}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("utf-8")



def render_resume_pdf(resume: TailoredResume) -> bytes:
    lines = _resume_lines(resume)
    usable_height = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN
    lines_per_page = max(int(usable_height // LINE_HEIGHT), 1)
    pages = _chunk_lines(lines, lines_per_page)

    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_id = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids: list[int] = []
    pages_root_id = len(pages) * 2 + 2  # reserved placement for Pages root after page/content objects

    for page_lines in pages:
        content = _content_stream(page_lines)
        content_id = add_object(b"<< /Length %d >>\nstream\n%b\nendstream" % (len(content), content))
        page_dict = (
            f"<< /Type /Page /Parent {pages_root_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("utf-8")
        page_id = add_object(page_dict)
        page_ids.append(page_id)

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_root_id = add_object(
        f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("utf-8")
    )
    catalog_id = add_object(f"<< /Type /Catalog /Pages {pages_root_id} 0 R >>".encode("utf-8"))

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("utf-8"))
        output.extend(obj)
        output.extend(b"\nendobj\n")

    xref_start = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("utf-8"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("utf-8"))
    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF"
        ).encode("utf-8")
    )
    return bytes(output)

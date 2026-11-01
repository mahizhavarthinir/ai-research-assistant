"""
Export Service for AI Research Assistant.
Generates professional, publication-grade reports in:
- PDF (.pdf) using ReportLab with custom page numbering and styled flowables.
- Word (.docx) using python-docx with styled typography, tables, and callouts.
- Markdown (.md) and JSON (.json).
"""

import io
import re
from datetime import datetime, timezone
from typing import Any

# ReportLab imports
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

# python-docx imports
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn


# ─────────────────────────────────────────────────────────────
# 1. ReportLab PDF Utilities
# ─────────────────────────────────────────────────────────────

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass ReportLab canvas to calculate total page count and
    render a modern header & footer with 'Page X of Y'.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Header rule & title on pages 2+
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.6)
            self.line(42, letter[1] - 40, letter[0] - 42, letter[1] - 40)
            self.drawString(42, letter[1] - 34, "AI Research Assistant — Verified Research Report")

        # Footer rule & page numbering on all pages
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.6)
        self.line(42, 45, letter[0] - 42, 45)

        self.drawString(42, 32, "Confidential & Source-Grounded Analysis | Generated with AI Research Assistant")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 42, 32, page_text)
        self.restoreState()


def _format_markdown_for_reportlab(text: str) -> str:
    """Escape XML characters and format markdown inline spans for ReportLab."""
    if not text:
        return ""
    # XML entity escaping
    s = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Bold **text** or __text__ -> <b>text</b>
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"__(.+?)__", r"<b>\1</b>", s)
    # Italic *text* or _text_ -> <i>text</i>
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", s)
    # Inline code `text`
    s = re.sub(r"`([^`]+?)`", r'<font face="Courier" color="#4338CA"><b>\1</b></font>', s)
    # Citation references [1] -> superscript or bold colored badge
    s = re.sub(r"\[(\d+)\]", r'<font color="#4F46E5"><b>[\1]</b></font>', s)
    return s


def _parse_markdown_into_pdf_flowables(content: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Parse markdown blocks into ReportLab flowables."""
    flowables = []
    lines = content.split("\n")
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            flowables.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#E2E8F0"), spaceBefore=8, spaceAfter=8))
            i += 1
            continue

        # Heading 1
        if stripped.startswith("# "):
            text = stripped[2:].strip()
            flowables.append(Paragraph(_format_markdown_for_reportlab(text), styles["H1"]))
            i += 1
            continue

        # Heading 2
        if stripped.startswith("## "):
            text = stripped[3:].strip()
            flowables.append(Paragraph(_format_markdown_for_reportlab(text), styles["H2"]))
            i += 1
            continue

        # Heading 3
        if stripped.startswith("### "):
            text = stripped[4:].strip()
            flowables.append(Paragraph(_format_markdown_for_reportlab(text), styles["H3"]))
            i += 1
            continue

        # Heading 4+
        if stripped.startswith("#### ") or stripped.startswith("##### "):
            text = stripped.lstrip("#").strip()
            flowables.append(Paragraph(_format_markdown_for_reportlab(text), styles["H4"]))
            i += 1
            continue

        # Blockquote (> text)
        if stripped.startswith(">"):
            quote_lines = []
            while i < total_lines and (lines[i].strip().startswith(">") or (lines[i].strip() and not lines[i].strip().startswith("#"))):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            quote_text = " ".join(quote_lines)
            p = Paragraph(_format_markdown_for_reportlab(quote_text), styles["Quote"])
            t = Table([[p]], colWidths=[letter[0] - 84])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor("#6366F1")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]))
            flowables.append(Spacer(1, 4))
            flowables.append(t)
            flowables.append(Spacer(1, 4))
            continue

        # Unordered bullet point
        if stripped.startswith(("- ", "* ", "• ")):
            bullet_text = stripped[2:].strip()
            p = Paragraph(f"&bull;&nbsp;&nbsp;{_format_markdown_for_reportlab(bullet_text)}", styles["Bullet"])
            flowables.append(p)
            i += 1
            continue

        # Ordered list (1. text, 2. text)
        num_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if num_match:
            num = num_match.group(1)
            item_text = num_match.group(2)
            p = Paragraph(f"<b>{num}.</b>&nbsp;&nbsp;{_format_markdown_for_reportlab(item_text)}", styles["Bullet"])
            flowables.append(p)
            i += 1
            continue

        # Normal paragraph (accumulate multi-line paragraphs)
        para_lines = [stripped]
        i += 1
        while i < total_lines:
            next_line = lines[i].strip()
            if not next_line or next_line.startswith(("#", ">", "-", "*", "•", "---")) or re.match(r"^\d+\.\s+", next_line):
                break
            para_lines.append(next_line)
            i += 1

        full_para = " ".join(para_lines)
        flowables.append(Paragraph(_format_markdown_for_reportlab(full_para), styles["Body"]))

    return flowables


def _get_pdf_styles() -> dict[str, ParagraphStyle]:
    """Configure modern typography styles for ReportLab."""
    sample = getSampleStyleSheet()
    
    return {
        "Title": ParagraphStyle(
            "ReportTitle",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=25,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4,
        ),
        "Subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=10,
        ),
        "SpeakerUser": ParagraphStyle(
            "SpeakerUser",
            parent=sample["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#0284C7"),
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "SpeakerAssistant": ParagraphStyle(
            "SpeakerAssistant",
            parent=sample["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#4F46E5"),
            spaceBefore=12,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "H1": ParagraphStyle(
            "CustomH1",
            parent=sample["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1E1B4B"),
            spaceBefore=12,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "H2": ParagraphStyle(
            "CustomH2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#312E81"),
            spaceBefore=9,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "H3": ParagraphStyle(
            "CustomH3",
            parent=sample["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceBefore=6,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "H4": ParagraphStyle(
            "CustomH4",
            parent=sample["Heading4"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#475569"),
            spaceBefore=5,
            spaceAfter=2,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "CustomBody",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#1E293B"),
            spaceAfter=6,
        ),
        "Bullet": ParagraphStyle(
            "CustomBullet",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=colors.HexColor("#1E293B"),
            leftIndent=14,
            spaceAfter=3,
        ),
        "Quote": ParagraphStyle(
            "CustomQuote",
            parent=sample["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        ),
        "CitationIndex": ParagraphStyle(
            "CitIndex",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#4338CA"),
            alignment=1,
        ),
        "CitationSource": ParagraphStyle(
            "CitSource",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        ),
        "CitationSnippet": ParagraphStyle(
            "CitSnippet",
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#475569"),
        ),
    }


def _build_citations_table_pdf(citations: list[dict], styles: dict[str, ParagraphStyle]) -> list[Any]:
    """Generate a clean ReportLab table for verified source citations."""
    if not citations:
        return []

    flowables = [
        Paragraph("Verified Source Citations", styles["H2"]),
        Paragraph("The following authoritative sources were retrieved and referenced during generation:", styles["Subtitle"]),
        Spacer(1, 4),
    ]

    table_data = [
        [
            Paragraph("<b>Ref</b>", styles["CitationIndex"]),
            Paragraph("<b>Document / Source URL</b>", styles["CitationSource"]),
            Paragraph("<b>Quoted Evidence &amp; Relevant Context</b>", styles["CitationSource"]),
        ]
    ]

    for c in citations:
        cit_idx = c.get("citation_index", 1)
        source_title = c.get("source_title") or "Source Document"
        page_num = c.get("page_number")
        page_info = f"<br/><font color='#64748B' size='8'>Page {page_num}</font>" if page_num else ""
        source_url = c.get("source_url")
        url_info = f"<br/><font color='#0284C7' size='7.5'>{source_url[:45]}...</font>" if source_url and len(source_url) > 45 else (f"<br/><font color='#0284C7' size='7.5'>{source_url}</font>" if source_url else "")
        snippet = (c.get("snippet") or "").strip()
        if len(snippet) > 300:
            snippet = snippet[:297] + "..."

        table_data.append([
            Paragraph(f"<b>[{cit_idx}]</b>", styles["CitationIndex"]),
            Paragraph(f"{_format_markdown_for_reportlab(source_title)}{page_info}{url_info}", styles["CitationSource"]),
            Paragraph(f"&ldquo;{_format_markdown_for_reportlab(snippet)}&rdquo;", styles["CitationSnippet"]),
        ])

    col_widths = [36, 170, letter[0] - 84 - 36 - 170]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#312E81")),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    flowables.append(t)
    flowables.append(Spacer(1, 10))
    return flowables


# ─────────────────────────────────────────────────────────────
# 2. python-docx Word Utilities
# ─────────────────────────────────────────────────────────────

def _set_cell_background(cell, hex_color: str):
    """Set background color of a table cell in docx."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tc_pr.append(shd)


def _set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner margins (padding) of a table cell in docx."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def _add_styled_paragraph_docx(doc: Document, text: str, style_type: str = "normal", left_indent: float = 0):
    """Parse inline bold/italic markdown into runs on a docx paragraph."""
    p = doc.add_paragraph()
    if left_indent > 0:
        p.paragraph_format.left_indent = Inches(left_indent)

    # Spacing
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15

    # Split by bold **text** and italic *text*
    # Regex splits while keeping delimiters
    tokens = re.split(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`)", text)
    for token in tokens:
        if not token:
            continue
        run = p.add_run()
        run.font.name = "Calibri"

        if token.startswith("**") and token.endswith("**") and len(token) >= 4:
            run.text = token[2:-2]
            run.bold = True
            run.font.color.rgb = RGBColor(15, 23, 42)
        elif token.startswith("*") and token.endswith("*") and len(token) >= 2:
            run.text = token[1:-1]
            run.italic = True
            run.font.color.rgb = RGBColor(51, 65, 85)
        elif token.startswith("`") and token.endswith("`") and len(token) >= 2:
            run.text = token[1:-1]
            run.font.name = "Consolas"
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(67, 56, 202)
        else:
            run.text = token
            if style_type == "quote":
                run.italic = True
                run.font.color.rgb = RGBColor(71, 85, 105)
            else:
                run.font.color.rgb = RGBColor(30, 41, 59)


def _parse_markdown_into_docx(doc: Document, content: str):
    """Parse markdown blocks into python-docx headings, paragraphs, and lists."""
    lines = content.split("\n")
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            p_rule = doc.add_paragraph()
            p_rule.paragraph_format.space_before = Pt(6)
            p_rule.paragraph_format.space_after = Pt(6)
            r = p_rule.add_run("____________________________________________________________________")
            r.font.color.rgb = RGBColor(226, 232, 240)
            r.font.size = Pt(8)
            i += 1
            continue

        # Heading 1
        if stripped.startswith("# "):
            text = stripped[2:].strip()
            h = doc.add_heading(level=1)
            h.paragraph_format.space_before = Pt(12)
            h.paragraph_format.space_after = Pt(4)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(text)
            r.font.name = "Calibri"
            r.font.size = Pt(15)
            r.font.bold = True
            r.font.color.rgb = RGBColor(30, 27, 75)
            i += 1
            continue

        # Heading 2
        if stripped.startswith("## "):
            text = stripped[3:].strip()
            h = doc.add_heading(level=2)
            h.paragraph_format.space_before = Pt(10)
            h.paragraph_format.space_after = Pt(3)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(text)
            r.font.name = "Calibri"
            r.font.size = Pt(13)
            r.font.bold = True
            r.font.color.rgb = RGBColor(49, 46, 129)
            i += 1
            continue

        # Heading 3
        if stripped.startswith("### "):
            text = stripped[4:].strip()
            h = doc.add_heading(level=3)
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(2)
            h.paragraph_format.keep_with_next = True
            r = h.add_run(text)
            r.font.name = "Calibri"
            r.font.size = Pt(11.5)
            r.font.bold = True
            r.font.color.rgb = RGBColor(51, 65, 85)
            i += 1
            continue

        # Blockquote (> text)
        if stripped.startswith(">"):
            quote_lines = []
            while i < total_lines and (lines[i].strip().startswith(">") or (lines[i].strip() and not lines[i].strip().startswith("#"))):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            quote_text = " ".join(quote_lines)

            # Single cell callout table
            tbl = doc.add_table(rows=1, cols=1)
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            cell = tbl.cell(0, 0)
            cell.width = Inches(6.8)
            _set_cell_background(cell, "F8FAFC")
            _set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
            
            p_cell = cell.paragraphs[0]
            p_cell.paragraph_format.space_after = Pt(2)
            r = p_cell.add_run(f"“{quote_text}”")
            r.font.name = "Calibri"
            r.font.italic = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(71, 85, 105)
            continue

        # Bullet list item
        if stripped.startswith(("- ", "* ", "• ")):
            bullet_text = stripped[2:].strip()
            _add_styled_paragraph_docx(doc, f"•  {bullet_text}", left_indent=0.25)
            i += 1
            continue

        # Numbered list item
        num_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if num_match:
            num = num_match.group(1)
            item_text = num_match.group(2)
            _add_styled_paragraph_docx(doc, f"{num}.  {item_text}", left_indent=0.25)
            i += 1
            continue

        # Normal paragraph
        para_lines = [stripped]
        i += 1
        while i < total_lines:
            next_line = lines[i].strip()
            if not next_line or next_line.startswith(("#", ">", "-", "*", "•", "---")) or re.match(r"^\d+\.\s+", next_line):
                break
            para_lines.append(next_line)
            i += 1

        _add_styled_paragraph_docx(doc, " ".join(para_lines))


def _build_citations_table_docx(doc: Document, citations: list[dict]):
    """Generate a clean docx table for verified source citations."""
    if not citations:
        return

    h = doc.add_heading(level=2)
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(4)
    r_h = h.add_run("Verified Source Citations")
    r_h.font.name = "Calibri"
    r_h.font.size = Pt(13)
    r_h.font.bold = True
    r_h.font.color.rgb = RGBColor(49, 46, 129)

    tbl = doc.add_table(rows=1, cols=3)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False

    # Header Row
    hdr_cells = tbl.rows[0].cells
    hdr_cells[0].width = Inches(0.6)
    hdr_cells[1].width = Inches(2.4)
    hdr_cells[2].width = Inches(3.8)

    hdr_titles = ["[#]", "Source Document", "Quoted Evidence / Excerpt"]
    for idx, text in enumerate(hdr_titles):
        _set_cell_background(hdr_cells[idx], "EEF2FF")
        _set_cell_margins(hdr_cells[idx], top=80, bottom=80, left=100, right=100)
        p = hdr_cells[idx].paragraphs[0]
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(49, 46, 129)

    for c in citations:
        row_cells = tbl.add_row().cells
        row_cells[0].width = Inches(0.6)
        row_cells[1].width = Inches(2.4)
        row_cells[2].width = Inches(3.8)

        for cell in row_cells:
            _set_cell_margins(cell, top=70, bottom=70, left=90, right=90)

        # Ref index
        p_idx = row_cells[0].paragraphs[0]
        r_idx = p_idx.add_run(f"[{c.get('citation_index', 1)}]")
        r_idx.font.name = "Calibri"
        r_idx.font.bold = True
        r_idx.font.color.rgb = RGBColor(79, 70, 229)

        # Source
        p_src = row_cells[1].paragraphs[0]
        r_src = p_src.add_run(c.get("source_title") or "Source Document")
        r_src.font.name = "Calibri"
        r_src.font.bold = True
        r_src.font.size = Pt(9)
        r_src.font.color.rgb = RGBColor(15, 23, 42)

        page_num = c.get("page_number")
        if page_num:
            r_page = p_src.add_run(f"\nPage {page_num}")
            r_page.font.size = Pt(8)
            r_page.font.color.rgb = RGBColor(100, 116, 139)

        source_url = c.get("source_url")
        if source_url:
            short_url = source_url[:35] + "..." if len(source_url) > 35 else source_url
            r_url = p_src.add_run(f"\n{short_url}")
            r_url.font.size = Pt(7.5)
            r_url.font.color.rgb = RGBColor(2, 132, 199)

        # Snippet
        p_snip = row_cells[2].paragraphs[0]
        snippet = (c.get("snippet") or "").strip()
        if len(snippet) > 280:
            snippet = snippet[:277] + "..."
        r_snip = p_snip.add_run(f"“{snippet}”")
        r_snip.font.name = "Calibri"
        r_snip.font.size = Pt(8.5)
        r_snip.font.color.rgb = RGBColor(71, 85, 105)


# ─────────────────────────────────────────────────────────────
# 3. High-Level Export Functions
# ─────────────────────────────────────────────────────────────

def export_conversation_to_pdf(conversation_title: str, messages: list[dict], created_at: str | None = None) -> bytes:
    """
    Export an entire chat conversation with research questions, assistant responses,
    headings, bullets, and verified citations to a publication-ready PDF document.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=42,
        rightMargin=42,
        topMargin=50,
        bottomMargin=55,
    )

    styles = _get_pdf_styles()
    timestamp_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    story: list[Any] = [
        Paragraph(conversation_title, styles["Title"]),
        Paragraph(f"<b>Exported:</b> {timestamp_str} &nbsp;|&nbsp; <b>Assistant Pipeline:</b> Source-Grounded RAG", styles["Subtitle"]),
        HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#6366F1"), spaceBefore=3, spaceAfter=12),
    ]

    for idx, msg in enumerate(messages):
        role = msg.get("role", "assistant")
        content = (msg.get("content") or "").strip()
        citations = msg.get("citations") or []

        if role == "user":
            story.append(Paragraph(f"User Query #{idx // 2 + 1}", styles["SpeakerUser"]))
            story.append(Paragraph(_format_markdown_for_reportlab(content), styles["Body"]))
            story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("AI Research Assistant Analysis", styles["SpeakerAssistant"]))
            # Parse markdown content preserving headings, bullets, quotes
            msg_flowables = _parse_markdown_into_pdf_flowables(content, styles)
            story.extend(msg_flowables)

            # Citations table if present
            if citations:
                cit_flowables = _build_citations_table_pdf(citations, styles)
                story.extend(cit_flowables)

            story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#E2E8F0"), spaceBefore=8, spaceAfter=10))

    doc.build(story, canvasmaker=NumberedCanvas)
    buf.seek(0)
    return buf.getvalue()


def export_conversation_to_docx(conversation_title: str, messages: list[dict], created_at: str | None = None) -> bytes:
    """
    Export an entire chat conversation with research questions, assistant responses,
    headings, bullets, and verified citations to a modern Word (.docx) document.
    """
    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Inches(0.8)
        sec.bottom_margin = Inches(0.8)
        sec.left_margin = Inches(0.8)
        sec.right_margin = Inches(0.8)

    # Title
    p_title = doc.add_paragraph()
    r_title = p_title.add_run(conversation_title)
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(21)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(15, 23, 42)
    p_title.paragraph_format.space_after = Pt(2)

    # Subtitle
    timestamp_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run(f"Exported: {timestamp_str} | AI Research Assistant")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(9.5)
    r_sub.font.color.rgb = RGBColor(100, 116, 139)
    p_sub.paragraph_format.space_after = Pt(14)

    for idx, msg in enumerate(messages):
        role = msg.get("role", "assistant")
        content = (msg.get("content") or "").strip()
        citations = msg.get("citations") or []

        if role == "user":
            h_user = doc.add_heading(level=2)
            h_user.paragraph_format.space_before = Pt(10)
            h_user.paragraph_format.space_after = Pt(3)
            r = h_user.add_run(f"Research Query #{idx // 2 + 1}")
            r.font.name = "Calibri"
            r.font.size = Pt(12)
            r.font.bold = True
            r.font.color.rgb = RGBColor(2, 132, 199)

            _add_styled_paragraph_docx(doc, content)
        else:
            h_assist = doc.add_heading(level=2)
            h_assist.paragraph_format.space_before = Pt(12)
            h_assist.paragraph_format.space_after = Pt(4)
            r = h_assist.add_run("AI Research Assistant Analysis")
            r.font.name = "Calibri"
            r.font.size = Pt(12.5)
            r.font.bold = True
            r.font.color.rgb = RGBColor(79, 70, 229)

            # Parse markdown content into headings, bullets, paragraphs
            _parse_markdown_into_docx(doc, content)

            # Citations
            if citations:
                _build_citations_table_docx(doc, citations)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def export_research_to_pdf(payload: dict) -> bytes:
    """
    Export a generated research report or multi-source comparison to PDF.
    Renders executive summary, key findings, analysis, methodology, conclusions,
    limitations, and source citations.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=42,
        rightMargin=42,
        topMargin=50,
        bottomMargin=55,
    )

    styles = _get_pdf_styles()
    title = payload.get("title") or "Comprehensive Research Report"
    topic = payload.get("topic") or ""
    summary = payload.get("executive_summary") or ""
    findings = payload.get("key_findings") or []
    conclusions = payload.get("conclusions") or ""
    limitations = payload.get("limitations") or ""
    content = payload.get("content") or ""
    citations = payload.get("citations") or []
    documents = payload.get("documents") or []

    timestamp_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    story: list[Any] = [
        Paragraph(title, styles["Title"]),
        Paragraph(f"<b>Generated:</b> {timestamp_str} &nbsp;|&nbsp; <b>Topic:</b> {topic or 'General Synthesis'}", styles["Subtitle"]),
        HRFlowable(width="100%", thickness=1.2, color=colors.HexColor("#6366F1"), spaceBefore=3, spaceAfter=10),
    ]

    # Analyzed Documents summary if available
    if documents:
        doc_names = ", ".join([d.get("filename") or "Document" for d in documents])
        p_docs = Paragraph(f"<b>Analyzed Sources ({len(documents)}):</b> {doc_names}", styles["Subtitle"])
        story.append(p_docs)
        story.append(Spacer(1, 4))

    # Executive Summary callout box
    if summary:
        story.append(Paragraph("Executive Summary", styles["H2"]))
        p_sum = Paragraph(_format_markdown_for_reportlab(summary), styles["Body"])
        t_sum = Table([[p_sum]], colWidths=[letter[0] - 84])
        t_sum.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2FF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#C7D2FE")),
        ]))
        story.append(t_sum)
        story.append(Spacer(1, 8))

    # Key Findings bullet callout
    if findings:
        story.append(Paragraph("Key Findings", styles["H2"]))
        for f in findings:
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{_format_markdown_for_reportlab(f)}", styles["Bullet"]))
        story.append(Spacer(1, 8))

    # Main Research Content (Analysis, Methodology, Strengths, Gaps)
    if content:
        story.append(Paragraph("Detailed Research Analysis & Findings", styles["H1"]))
        flowables = _parse_markdown_into_pdf_flowables(content, styles)
        story.extend(flowables)

    # Conclusions & Limitations
    if conclusions or limitations:
        story.append(Paragraph("Conclusions & Research Limitations", styles["H2"]))
        if conclusions:
            story.append(Paragraph(_format_markdown_for_reportlab(conclusions), styles["Body"]))
        if limitations:
            story.append(Paragraph(f"<b>Limitations &amp; Gaps:</b> {_format_markdown_for_reportlab(limitations)}", styles["Body"]))
        story.append(Spacer(1, 6))

    # Citations Table
    if citations:
        cit_flowables = _build_citations_table_pdf(citations, styles)
        story.extend(cit_flowables)

    doc.build(story, canvasmaker=NumberedCanvas)
    buf.seek(0)
    return buf.getvalue()


def export_research_to_docx(payload: dict) -> bytes:
    """
    Export a generated research report or multi-source comparison to Word (.docx).
    Renders executive summary, key findings, analysis, methodology, conclusions,
    limitations, and source citations.
    """
    doc = Document()
    for sec in doc.sections:
        sec.top_margin = Inches(0.8)
        sec.bottom_margin = Inches(0.8)
        sec.left_margin = Inches(0.8)
        sec.right_margin = Inches(0.8)

    title = payload.get("title") or "Comprehensive Research Report"
    topic = payload.get("topic") or ""
    summary = payload.get("executive_summary") or ""
    findings = payload.get("key_findings") or []
    conclusions = payload.get("conclusions") or ""
    limitations = payload.get("limitations") or ""
    content = payload.get("content") or ""
    citations = payload.get("citations") or []
    documents = payload.get("documents") or []

    # Title
    p_title = doc.add_paragraph()
    r_title = p_title.add_run(title)
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(21)
    r_title.font.bold = True
    r_title.font.color.rgb = RGBColor(15, 23, 42)
    p_title.paragraph_format.space_after = Pt(2)

    # Subtitle
    timestamp_str = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    p_sub = doc.add_paragraph()
    r_sub = p_sub.add_run(f"Generated: {timestamp_str} | Topic: {topic or 'Research Analysis'}")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(9.5)
    r_sub.font.color.rgb = RGBColor(100, 116, 139)
    p_sub.paragraph_format.space_after = Pt(12)

    # Sources summary
    if documents:
        doc_names = ", ".join([d.get("filename") or "Document" for d in documents])
        p_docs = doc.add_paragraph()
        r_docs_lbl = p_docs.add_run(f"Analyzed Sources ({len(documents)}): ")
        r_docs_lbl.font.bold = True
        p_docs.add_run(doc_names)
        p_docs.paragraph_format.space_after = Pt(10)

    # Executive Summary Box
    if summary:
        h_sum = doc.add_heading(level=2)
        h_sum.paragraph_format.space_before = Pt(8)
        h_sum.paragraph_format.space_after = Pt(3)
        r_sum_h = h_sum.add_run("Executive Summary")
        r_sum_h.font.name = "Calibri"
        r_sum_h.font.size = Pt(13)
        r_sum_h.font.bold = True
        r_sum_h.font.color.rgb = RGBColor(49, 46, 129)

        tbl = doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        cell.width = Inches(6.8)
        _set_cell_background(cell, "EEF2FF")
        _set_cell_margins(cell, top=100, bottom=100, left=150, right=150)
        p_cell = cell.paragraphs[0]
        r_c = p_cell.add_run(summary)
        r_c.font.name = "Calibri"
        r_c.font.size = Pt(10)
        r_c.font.color.rgb = RGBColor(30, 41, 59)

    # Key Findings
    if findings:
        h_find = doc.add_heading(level=2)
        h_find.paragraph_format.space_before = Pt(12)
        h_find.paragraph_format.space_after = Pt(3)
        r_find = h_find.add_run("Key Findings")
        r_find.font.name = "Calibri"
        r_find.font.size = Pt(13)
        r_find.font.bold = True
        r_find.font.color.rgb = RGBColor(49, 46, 129)

        for f in findings:
            _add_styled_paragraph_docx(doc, f"•  {f}", left_indent=0.2)

    # Detailed Analysis Content
    if content:
        h_cnt = doc.add_heading(level=1)
        h_cnt.paragraph_format.space_before = Pt(14)
        h_cnt.paragraph_format.space_after = Pt(4)
        r_cnt = h_cnt.add_run("Detailed Research Analysis & Findings")
        r_cnt.font.name = "Calibri"
        r_cnt.font.size = Pt(15)
        r_cnt.font.bold = True
        r_cnt.font.color.rgb = RGBColor(30, 27, 75)

        _parse_markdown_into_docx(doc, content)

    # Conclusions & Limitations
    if conclusions or limitations:
        h_conc = doc.add_heading(level=2)
        h_conc.paragraph_format.space_before = Pt(12)
        h_conc.paragraph_format.space_after = Pt(3)
        r_c = h_conc.add_run("Conclusions & Research Limitations")
        r_c.font.name = "Calibri"
        r_c.font.size = Pt(13)
        r_c.font.bold = True
        r_c.font.color.rgb = RGBColor(49, 46, 129)

        if conclusions:
            _add_styled_paragraph_docx(doc, conclusions)
        if limitations:
            _add_styled_paragraph_docx(doc, f"Limitations & Gaps: {limitations}")

    # Citations
    if citations:
        _build_citations_table_docx(doc, citations)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


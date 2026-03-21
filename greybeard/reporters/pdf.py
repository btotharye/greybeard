"""PDF reporter for greybeard review results."""

from __future__ import annotations

from typing import Any

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

from greybeard.formatters import ReviewMetadata, _parse_bullets, _parse_sections


def _check_reportlab() -> None:
    """Ensure reportlab is available."""
    if not HAS_REPORTLAB:
        raise ImportError(
            "reportlab is required for PDF export. Install with: pip install reportlab"
        )


class PDFReporter:
    """Generate professional PDF reports for greybeard reviews."""

    def __init__(self, markdown: str, meta: ReviewMetadata, pagesize: Any = None):
        """Initialize the PDF reporter."""
        _check_reportlab()
        if pagesize is None:
            pagesize = letter
        self.COLOR_HEADER = colors.HexColor("#2C3E50")
        self.COLOR_ACCENT = colors.HexColor("#9B59B6")
        self.COLOR_LIGHT_BG = colors.HexColor("#ECF0F1")
        self.COLOR_BORDER = colors.HexColor("#BDC3C7")
        self.COLOR_TEXT = colors.HexColor("#2C3E50")
        self.markdown = markdown
        self.meta = meta
        self.pagesize = pagesize
        self.width, self.height = pagesize
        self.sections = _parse_sections(markdown)
        self._setup_styles()

    def _setup_styles(self) -> None:
        """Set up reportlab paragraph and table styles."""
        base_styles = getSampleStyleSheet()
        self.styles: StyleSheet1 = StyleSheet1()

        for name in base_styles.byName:
            self.styles.add(base_styles[name])

        self.styles.add(
            ParagraphStyle(
                name="CustomHeading1",
                parent=base_styles["Heading1"],
                fontSize=24,
                textColor=self.COLOR_HEADER,
                spaceAfter=12,
                fontName="Helvetica-Bold",
                leading=28,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomHeading2",
                parent=base_styles["Heading2"],
                fontSize=14,
                textColor=self.COLOR_ACCENT,
                spaceAfter=8,
                spaceBefore=8,
                fontName="Helvetica-Bold",
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomBody",
                parent=base_styles["BodyText"],
                fontSize=10,
                textColor=self.COLOR_TEXT,
                spaceAfter=6,
                leading=12,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="Metadata",
                parent=base_styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#7F8C8D"),
                alignment=TA_CENTER,
            )
        )

    def _build_title_page(self) -> list:
        """Build the title/cover page content."""
        story = []
        story.append(Spacer(self.width, 0.5 * inch))

        title = Paragraph(
            "🧙 <b>greybeard</b> Review Report",
            self.styles["CustomHeading1"],
        )
        story.append(title)
        story.append(Spacer(self.width, 0.2 * inch))

        mode_display = self.meta.mode.replace("_", " ").title()
        info_text = f"<b>Mode:</b> {mode_display} | <b>Pack:</b> {self.meta.pack_name}"
        story.append(Paragraph(info_text, self.styles["CustomBody"]))
        story.append(Spacer(self.width, 0.3 * inch))

        meta_data = [
            ["Generated", self.meta.generated_at],
            ["LLM Backend", self.meta.backend],
            ["Model", self.meta.model],
        ]

        meta_table = Table(meta_data, colWidths=[1.5 * inch, 3 * inch])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), self.COLOR_LIGHT_BG),
                    ("TEXTCOLOR", (0, 0), (-1, -1), self.COLOR_TEXT),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 1, self.COLOR_BORDER),
                ]
            )
        )
        story.append(meta_table)
        story.append(PageBreak())

        return story

    def _build_risk_summary(self) -> list:
        """Build the risk summary section."""
        story = []
        story.append(Paragraph("Risk Summary", self.styles["CustomHeading2"]))

        summary = self.sections.get("summary", "No summary available.")
        story.append(Paragraph(summary, self.styles["CustomBody"]))

        key_risks = self.sections.get("key_risks", "")
        risk_items = _parse_bullets(key_risks)

        if risk_items:
            story.append(Spacer(self.width, 0.15 * inch))
            story.append(Paragraph("<b>Identified Risks:</b>", self.styles["CustomBody"]))

            risk_table_data = [["Risk", "Severity"]]
            for risk in risk_items[:10]:
                severity = (
                    "🔴 Critical"
                    if any(
                        kw in risk.lower()
                        for kw in ["no plan", "unknown", "critical", "fail", "loss"]
                    )
                    else "🟠 High"
                    if any(kw in risk.lower() for kw in ["risk", "issue", "concern"])
                    else "🟡 Medium"
                )

                risk_table_data.append([risk, severity])

            risk_table = Table(risk_table_data, colWidths=[4 * inch, 1.5 * inch])
            risk_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), self.COLOR_ACCENT),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.COLOR_LIGHT_BG]),
                        ("GRID", (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
                    ]
                )
            )
            story.append(risk_table)

        story.append(Spacer(self.width, 0.2 * inch))
        return story

    def _build_findings_section(self) -> list:
        """Build detailed findings and tradeoffs section."""
        story = []
        story.append(Paragraph("Detailed Analysis", self.styles["CustomHeading2"]))

        tradeoffs = self.sections.get("tradeoffs", "")
        if tradeoffs:
            story.append(Paragraph("<b>Tradeoffs & Considerations:</b>", self.styles["CustomBody"]))
            story.append(Paragraph(tradeoffs, self.styles["CustomBody"]))
            story.append(Spacer(self.width, 0.1 * inch))

        questions = self.sections.get("questions", "")
        if questions:
            story.append(
                Paragraph(
                    "<b>Questions to Answer Before Proceeding:</b>",
                    self.styles["CustomBody"],
                )
            )
            question_items = _parse_bullets(questions)
            if question_items:
                question_data = [[f"{i + 1}. {q}"] for i, q in enumerate(question_items[:8])]
                question_table = Table(question_data, colWidths=[5.5 * inch])
                question_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), self.COLOR_LIGHT_BG),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("GRID", (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
                        ]
                    )
                )
                story.append(question_table)
            else:
                story.append(Paragraph(questions, self.styles["CustomBody"]))

        comm = self.sections.get("communication_language", "")
        if comm:
            story.append(
                Paragraph("<b>Suggested Communication Language:</b>", self.styles["CustomBody"])
            )
            story.append(Paragraph(f"<i>{comm}</i>", self.styles["CustomBody"]))

        story.append(Spacer(self.width, 0.2 * inch))
        return story

    def _build_metadata_footer(self) -> list:
        """Build the metadata footer section."""
        story = []
        story.append(PageBreak())
        story.append(Spacer(self.width, 0.5 * inch))
        story.append(Paragraph("Report Details", self.styles["CustomHeading2"]))

        details = [
            ["Mode", self.meta.mode],
            ["Content Pack", self.meta.pack_name],
            ["LLM Backend", self.meta.backend],
            ["Model", self.meta.model],
            ["Generated", self.meta.generated_at],
        ]

        details_table = Table(details, colWidths=[2 * inch, 3.5 * inch])
        details_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), self.COLOR_LIGHT_BG),
                    ("TEXTCOLOR", (0, 0), (-1, -1), self.COLOR_TEXT),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, self.COLOR_BORDER),
                ]
            )
        )
        story.append(details_table)
        story.append(Spacer(self.width, 0.3 * inch))

        footer_text = (
            "<i>This report was generated by greybeard, a staff-level review assistant.</i>"
        )
        story.append(Paragraph(footer_text, self.styles["Metadata"]))

        return story

    def generate(self, output_path: str) -> str:
        """Generate the PDF report."""
        story = []
        story.extend(self._build_title_page())
        story.extend(self._build_risk_summary())
        story.extend(self._build_findings_section())
        story.extend(self._build_metadata_footer())

        doc = SimpleDocTemplate(
            output_path,
            pagesize=self.pagesize,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        doc.build(story)
        return output_path


def to_pdf(markdown: str, meta: ReviewMetadata, output_path: str | None = None) -> str:
    """Convert a markdown review to a professional PDF report."""
    if not output_path:
        raise ValueError("output_path is required for PDF export")

    reporter = PDFReporter(markdown, meta)
    return reporter.generate(output_path)

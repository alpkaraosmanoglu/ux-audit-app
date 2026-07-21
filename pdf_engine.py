"""PDF engine — renders the on-screen audit review page (findings +
benchmark section) as a downloadable PDF, using reportlab (pure Python, no
system dependencies like LibreOffice/wkhtmltopdf).

This mirrors the Streamlit review page itself — same content, same
severity/verification color language as styles.py — rather than the
stakeholder-presentation design used by deck_engine.py. Think of it as
"export this page," not "build a deck."
"""

import io
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from audit_engine import VERIFICATION_TAG_RE, extract_benchmark_section, tally_string

# ---------------------------------------------------------------------------
# Brand — mirrors the Studio's own on-screen palette (styles.py), not the
# adesso deck branding used for the exported presentation.
# ---------------------------------------------------------------------------
DARK_HEX = "#0b0b0c"
MUTED_HEX = "#71717a"
BORDER_HEX = "#e4e4e7"
BODY_TEXT_HEX = "#3f3f46"
CITE_BG_HEX = "#f4f4f5"

DARK = HexColor(DARK_HEX)
MUTED = HexColor(MUTED_HEX)
BORDER = HexColor(BORDER_HEX)
BODY_TEXT = HexColor(BODY_TEXT_HEX)

SEVERITY_HEX = {
    "major": ("#a3271d", "#fef2f2"),
    "mid": ("#a3671d", "#fffbeb"),
    "minor": ("#8a7a12", "#fefce8"),
    "open": ("#2f5fa3", "#eff6ff"),
}
VERIFICATION_HEX = {
    "Verified": ("#16a34a", "\u2713 VERIFIED"),
    "Unverified": (MUTED_HEX, "? UNVERIFIED"),
    "Outdated?": ("#b45309", "! OUTDATED?"),
}

LABELS = {
    "English": {
        "finding": "Finding", "suggestions": "Suggestions", "solution": "Solution",
        "heuristic": "Heuristic", "benchmarks": "Benchmarks",
        "market_benchmark": "Market Benchmark", "competitor_benchmark": "Competitor Benchmark",
        "legend": "Verified via web search \u00b7 Unverified \u2014 drafted, not confirmed \u00b7 Possibly outdated",
        "evidence": "Evidence",
    },
    "Türkçe": {
        "finding": "Tespit", "suggestions": "Öneriler", "solution": "Çözüm",
        "heuristic": "Sezgisel kural", "benchmarks": "Kıyaslamalar",
        "market_benchmark": "Pazar Kıyaslaması", "competitor_benchmark": "Rakip Kıyaslaması",
        "legend": "Web aramasıyla doğrulandı \u00b7 Doğrulanmadı \u2014 eğitim verisinden yazıldı \u00b7 Güncelliğini yitirmiş olabilir",
        "evidence": "Kanıt",
    },
    "Deutsch": {
        "finding": "Befund", "suggestions": "Vorschläge", "solution": "Lösung",
        "heuristic": "Heuristik", "benchmarks": "Benchmarks",
        "market_benchmark": "Marktvergleich", "competitor_benchmark": "Wettbewerbsvergleich",
        "legend": "Per Websuche bestätigt \u00b7 Unbestätigt \u2014 aus Trainingswissen verfasst \u00b7 Möglicherweise veraltet",
        "evidence": "Beleg",
    },
}

EVIDENCE_LINE_RE = re.compile(
    r"\*\*(?:Evidence reference|Kanıt referansı|Beleg)\s*:?\*\*\s*.+?(?:\n|$)"
)
SCREENSHOT_NAME_RE = re.compile(r"(\S+\.(?:png|jpg|jpeg|webp))", re.IGNORECASE)

PAGE_W, PAGE_H = A4
MARGIN = 0.7 * inch


def _labels(language: str) -> dict:
    return LABELS.get(language, LABELS["English"])


# ---------------------------------------------------------------------------
# Paragraph styles
# ---------------------------------------------------------------------------
H1_STYLE = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, textColor=DARK, leading=24)
CAPTION_STYLE = ParagraphStyle("caption", fontName="Helvetica", fontSize=9.5, textColor=MUTED, leading=13)
TALLY_STYLE = ParagraphStyle("tally", fontName="Helvetica", fontSize=9.5, textColor=MUTED)
FINDING_TITLE_STYLE = ParagraphStyle("finding_title", fontName="Helvetica-Bold", fontSize=14, textColor=DARK, leading=17)
BODY_STYLE = ParagraphStyle("body", fontName="Helvetica", fontSize=10, textColor=BODY_TEXT, leading=14.5, spaceAfter=6)
CITE_STYLE = ParagraphStyle("cite", fontName="Helvetica-Oblique", fontSize=8.5, textColor=MUTED, leading=12)
EVIDENCE_STYLE = ParagraphStyle("evidence", fontName="Helvetica-Oblique", fontSize=8.5, textColor=MUTED, leading=12)
IDX_STYLE = ParagraphStyle("idx", fontName="Helvetica", fontSize=8.5, textColor=MUTED, alignment=TA_RIGHT)
SECTION_TITLE_STYLE = ParagraphStyle("section_title", fontName="Helvetica-Bold", fontSize=16, textColor=DARK, spaceAfter=4)
LEGEND_STYLE = ParagraphStyle("legend", fontName="Helvetica-Oblique", fontSize=8.5, textColor=MUTED, spaceAfter=6)
BENCH_BODY_STYLE = ParagraphStyle("bench_body", fontName="Helvetica", fontSize=10, textColor=BODY_TEXT, leading=14.5)


def _esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _md_inline_to_markup(text: str) -> str:
    """Small Markdown -> reportlab-markup converter: bold + bullets + line
    breaks. Escapes XML first, then re-applies **bold** as <b>."""
    text = _esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"^-\s+", "\u2022  ", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    return text


def _paragraphs_from_body(body: str) -> list[str]:
    """Split a finding body into paragraph-level markup chunks (blank-line
    separated), each with single newlines converted to <br/>."""
    body = EVIDENCE_LINE_RE.sub("", body or "").strip()
    chunks = [c for c in re.split(r"\n\s*\n", body) if c.strip()]
    out = []
    for c in chunks:
        c = _md_inline_to_markup(c)
        c = c.replace("\n", "<br/>")
        out.append(c)
    return out


def _tagged_markup(text: str) -> str:
    """Render inline [Verified]/[Unverified]/[Outdated?] tags as small
    colored bold badges within reportlab Paragraph markup."""
    text = _md_inline_to_markup(text)

    def _tag_sub(m):
        fg_hex, label = VERIFICATION_HEX[m.group(1)]
        return f'<font color="{fg_hex}"><b> {label} </b></font>'

    return VERIFICATION_TAG_RE.sub(_tag_sub, text)


def _fit_image(data: bytes, max_w: float, max_h: float) -> Image:
    from PIL import Image as PILImage

    with PILImage.open(io.BytesIO(data)) as im:
        iw, ih = im.size
    scale = min(max_w / iw, max_h / ih)
    return Image(io.BytesIO(data), width=iw * scale, height=ih * scale)


def _badge_table(label: str, fg_hex: str, bg_hex: str) -> Table:
    style = ParagraphStyle(
        "badge", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=HexColor(fg_hex), leading=10,
    )
    t = Table([[Paragraph(label, style)]])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(bg_hex)),
        ("BOX", (0, 0), (-1, -1), 1, HexColor(fg_hex)),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def _resolve_screenshot(finding: dict, screenshots: list[dict]):
    idx = finding.get("screenshot_index")
    if idx and 1 <= idx <= len(screenshots):
        return screenshots[idx - 1]
    ev = finding.get("evidence", "")
    match = SCREENSHOT_NAME_RE.search(ev) if ev else None
    if match:
        name = match.group(1).lower()
        for s in screenshots:
            if s["name"].lower() == name or name in s["name"].lower():
                return s
    return None


def _finding_flowables(finding: dict, shot, labels: dict, idx: int, total: int) -> list:
    fg_hex, bg_hex = SEVERITY_HEX.get(finding["severity"], SEVERITY_HEX["open"])
    flow = []

    header = Table(
        [[_badge_table(finding["severity_raw"].upper(), fg_hex, bg_hex),
          Paragraph(f"{idx:02d} / {total:02d}", IDX_STYLE)]],
        colWidths=[None, PAGE_W - 2 * MARGIN - 1.2 * inch],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    title_block = [header, Spacer(1, 6), Paragraph(_esc(finding["title"]), FINDING_TITLE_STYLE), Spacer(1, 6)]
    flow.append(KeepTogether(title_block))

    body_paras = _paragraphs_from_body(finding.get("body", ""))
    body_flow = [Paragraph(bp, BODY_STYLE) for bp in body_paras]

    if shot:
        img_w = 1.9 * inch
        img_flowable = _fit_image(shot["data"], max_w=img_w, max_h=1.9 * inch)
        text_w = PAGE_W - 2 * MARGIN - img_w - 0.25 * inch
        row_table = Table([[img_flowable, body_flow]], colWidths=[img_w, text_w])
        row_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 0.25 * inch),
            ("LEFTPADDING", (1, 0), (1, 0), 0),
            ("RIGHTPADDING", (1, 0), (1, 0), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        flow.append(row_table)
    else:
        ev = finding.get("evidence", "").strip()
        if ev:
            flow.append(Paragraph(f"{_esc(labels['evidence'])}: {_esc(ev)}", EVIDENCE_STYLE))
            flow.append(Spacer(1, 4))
        flow.extend(body_flow)

    if finding.get("heuristic"):
        cite_table = Table([[Paragraph(_esc(finding["heuristic"]), CITE_STYLE)]],
                            colWidths=[PAGE_W - 2 * MARGIN])
        cite_table.setStyle(TableStyle([
            ("LINEBEFORE", (0, 0), (0, 0), 2, DARK),
            ("BACKGROUND", (0, 0), (-1, -1), HexColor(CITE_BG_HEX)),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        flow.append(Spacer(1, 8))
        flow.append(cite_table)

    flow.append(Spacer(1, 10))
    flow.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    flow.append(Spacer(1, 14))
    return flow


def _benchmark_flowables(audit_text: str, labels: dict, benchmark_scope: str) -> list:
    section = extract_benchmark_section(audit_text)
    if not section:
        return []

    text = re.sub(r"^##\s+.+\n?", "", section.strip(), count=1)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    title = {
        "market": labels["market_benchmark"],
        "competitors": labels["competitor_benchmark"],
    }.get(benchmark_scope, labels["benchmarks"])

    flow = [
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1.5, color=DARK),
        Spacer(1, 10),
        Paragraph(_esc(title), SECTION_TITLE_STYLE),
        Paragraph(_esc(labels["legend"]), LEGEND_STYLE),
        Spacer(1, 6),
    ]
    for para in paragraphs:
        lines = [ln.strip("-\u2022 ").strip() for ln in para.split("\n") if ln.strip()]
        for line in lines:
            flow.append(Paragraph("\u2022  " + _tagged_markup(line), BENCH_BODY_STYLE))
            flow.append(Spacer(1, 6))
    return flow


def generate_audit_pdf(
    product_name: str,
    language: str,
    mode: str,
    benchmark: str,
    findings: list[dict],
    tally: dict[str, int],
    screenshots: list[dict],
    audit_text: str,
) -> bytes:
    """Render the audit review page (findings + benchmark section) as a PDF.

    Mirrors what's shown on screen in the "audit" step of the app — same
    findings, same severity/verification colors — as a shareable document.
    """
    labels = _labels(language)
    screenshots = screenshots or []
    findings = findings or []

    mode_labels = {"screenshots": "Screenshots", "urls": "URLs only", "hybrid": "Hybrid"}
    bench_labels = {"none": "No benchmarking", "market": "Market", "competitors": "Competitors", "both": "Market + Competitors"}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
        title=f"UX Audit — {product_name}",
    )

    story = [
        Paragraph(_esc(f"UX Audit \u2014 {product_name}"), H1_STYLE),
        Paragraph(
            _esc(
                f"{mode_labels.get(mode, mode)} mode \u00b7 {language} \u00b7 "
                f"{bench_labels.get(benchmark, 'None')} \u00b7 "
                f"Generated {datetime.now().strftime('%b %d, %Y')}"
            ),
            CAPTION_STYLE,
        ),
        Spacer(1, 4),
    ]
    if tally:
        story.append(Paragraph(_esc(tally_string(tally, language)), TALLY_STYLE))
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=1.5, color=DARK))
    story.append(Spacer(1, 14))

    for i, f in enumerate(findings, start=1):
        shot = _resolve_screenshot(f, screenshots)
        story.extend(_finding_flowables(f, shot, labels, i, len(findings)))

    if benchmark != "none":
        story.extend(_benchmark_flowables(audit_text, labels, benchmark))

    def _on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 0.45 * inch, product_name)
        canvas.drawRightString(PAGE_W - MARGIN, 0.45 * inch, f"Page {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()

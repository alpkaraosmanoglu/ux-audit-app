"""Deck engine — generates a .pptx presentation from a completed UX audit.

Uses the adesso template and the pptx_helpers patterns. Produces an editable
.pptx file. PDF conversion is skipped on Streamlit Cloud (no LibreOffice).
"""

import io
import os
import pathlib
import re
import sys
import tempfile
import zipfile
from datetime import datetime

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN

_SCRIPTS_DIR = pathlib.Path(__file__).parent / "skills" / "ux-audit-deck-skill" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from pptx_helpers import (
    add_slide,
    delete_slide,
    dedup_zip,
    insert_image_fit,
    set_body_lines,
    set_title,
)

ASSETS_DIR = pathlib.Path(__file__).parent / "skills" / "ux-audit-deck-skill" / "assets"
TEMPLATE_PATH = ASSETS_DIR / "adesso_template.pptx"

# Layout indices in the adesso template
LAYOUT_COVER = 2          # Titleslide BLUE
LAYOUT_CONTENT = 14       # Title and Content WHITE
LAYOUT_SECTION = 8        # Section Header WHITE
LAYOUT_PICTURE = 20       # Content with Picture WHITE
LAYOUT_TWO_CONTENT = 16   # Two Content WHITE
LAYOUT_CLOSING = 28       # Claim WHITE

# Placeholder indices
PH_TITLE = 0
PH_SUBTITLE = 1
PH_BODY_CONTENT = 17      # body on layout 14
PH_BODY_PICTURE = 1       # body text on layout 20
PH_PICTURE = 18            # picture on layout 20

# Language-specific labels
LABELS = {
    "English": {
        "report_title": "{product} — UX Audit Report",
        "overview": "Overview",
        "major_findings": "Major Findings",
        "mid_findings": "Mid Findings",
        "minor_findings": "Minor Findings",
        "open_findings": "Open Questions",
        "findings_count": "{n} finding(s) at this severity",
        "benchmarks": "Benchmarks",
        "market_benchmark": "Market Benchmark",
        "competitor_benchmark": "Competitor Benchmark",
        "closing": "Thank you",
        "closing_body": "Next steps: review findings with the team, prioritize by severity, and schedule validation research for the top items.",
        "pages_reviewed": "Pages reviewed",
        "target_users": "Target users",
        "mode": "Mode",
        "severity_tally": "Severity tally",
        "benchmark_scope": "Benchmark scope",
        "finding": "Finding",
        "suggestions": "Suggestions",
        "solution": "Solution",
        "heuristic": "Heuristic",
    },
    "Türkçe": {
        "report_title": "{product} — UX Denetim Raporu",
        "overview": "Genel Bakış",
        "major_findings": "Önemli Tespitler",
        "mid_findings": "Orta Tespitler",
        "minor_findings": "Hafif Tespitler",
        "open_findings": "Açık Sorular",
        "findings_count": "Bu düzeyde {n} tespit",
        "benchmarks": "Kıyaslamalar",
        "market_benchmark": "Pazar Kıyaslaması",
        "competitor_benchmark": "Rakip Kıyaslaması",
        "closing": "Teşekkürler",
        "closing_body": "Sonraki adımlar: tespitleri ekiple gözden geçirin, önem derecesine göre önceliklendirin ve en önemli maddeleri doğrulama araştırmasına planlayın.",
        "pages_reviewed": "İncelenen sayfalar",
        "target_users": "Hedef kullanıcılar",
        "mode": "Mod",
        "severity_tally": "Tespit dağılımı",
        "benchmark_scope": "Kıyaslama kapsamı",
        "finding": "Tespit",
        "suggestions": "Öneriler",
        "solution": "Çözüm",
        "heuristic": "Sezgisel kural",
    },
    "Deutsch": {
        "report_title": "{product} — UX-Audit-Bericht",
        "overview": "Überblick",
        "major_findings": "Wichtige Befunde",
        "mid_findings": "Mittlere Befunde",
        "minor_findings": "Geringfügige Befunde",
        "open_findings": "Offene Fragen",
        "findings_count": "{n} Befund(e) auf dieser Stufe",
        "benchmarks": "Benchmarks",
        "market_benchmark": "Marktvergleich",
        "competitor_benchmark": "Wettbewerbsvergleich",
        "closing": "Vielen Dank",
        "closing_body": "Nächste Schritte: Befunde im Team besprechen, nach Schweregrad priorisieren und Validierungsforschung für die wichtigsten Punkte planen.",
        "pages_reviewed": "Geprüfte Seiten",
        "target_users": "Zielnutzer",
        "mode": "Modus",
        "severity_tally": "Befundverteilung",
        "benchmark_scope": "Benchmark-Umfang",
        "finding": "Befund",
        "suggestions": "Vorschläge",
        "solution": "Lösung",
        "heuristic": "Heuristik",
    },
}

SEVERITY_SECTION_KEYS = [
    ("major", "major_findings"),
    ("mid", "mid_findings"),
    ("minor", "minor_findings"),
    ("open", "open_findings"),
]


def _get_labels(language: str) -> dict:
    return LABELS.get(language, LABELS["English"])


def _fix_template(template_path: str) -> str:
    """Fix the content type in the template if needed.

    Returns the path to a usable template file.
    """
    fixed_path = os.path.join(tempfile.gettempdir(), "adesso_template_fixed.pptx")

    with zipfile.ZipFile(template_path, "r") as zin:
        with zipfile.ZipFile(fixed_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "[Content_Types].xml":
                    data = data.replace(
                        b"presentationml.template.main+xml",
                        b"presentationml.presentation.main+xml",
                    )
                zout.writestr(item, data)

    return fixed_path


def generate_deck(
    findings: list[dict],
    product_name: str,
    language: str,
    mode: str,
    benchmark: str,
    screenshots: dict[str, bytes] | None = None,
    tally: dict[str, int] | None = None,
    target_users: str = "",
    pages_reviewed: str = "",
    benchmark_text: str = "",
    progress_callback=None,
) -> bytes:
    """Generate a .pptx deck from structured findings.

    Args:
        findings: list of parsed finding dicts from audit_engine.parse_findings
        product_name: name for the cover slide
        language: 'English', 'Türkçe', or 'Deutsch'
        mode: 'screenshots', 'urls', or 'hybrid'
        benchmark: 'none', 'market', 'competitors', or 'both'
        screenshots: dict mapping screenshot name to image bytes
        tally: severity tally dict
        target_users: for the overview slide
        pages_reviewed: for the overview slide
        benchmark_text: raw benchmark section text from the audit
        progress_callback: callable(current, total, label) for progress updates

    Returns:
        bytes of the generated .pptx file
    """
    labels = _get_labels(language)
    screenshots = screenshots or {}

    # Prepare template
    template = str(TEMPLATE_PATH)
    try:
        prs = Presentation(template)
    except Exception:
        template = _fix_template(template)
        prs = Presentation(template)

    # Calculate total slides for progress
    total_sections = sum(1 for sev, _ in SEVERITY_SECTION_KEYS
                         if any(f["severity"] == sev for f in findings))
    total_slides = 2 + total_sections + len(findings) + 1  # cover + overview + sections + findings + closing
    if benchmark != "none":
        total_slides += 2  # section divider + content
    current_slide = 0

    def _progress(label):
        nonlocal current_slide
        current_slide += 1
        if progress_callback:
            progress_callback(current_slide, total_slides, label)

    # Delete all existing template slides
    while len(prs.slides) > 0:
        delete_slide(prs, 0)

    # --- 1. Cover slide ---
    slide = add_slide(prs, LAYOUT_COVER)
    set_title(slide, labels["report_title"].format(product=product_name))
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == PH_SUBTITLE:
            ph.text = datetime.now().strftime("%B %Y")
            break
    _progress("Cover")

    # --- 2. Overview slide ---
    slide = add_slide(prs, LAYOUT_CONTENT)
    set_title(slide, labels["overview"])
    overview_lines = []
    if pages_reviewed:
        overview_lines.append((labels["pages_reviewed"], pages_reviewed))
    if target_users:
        overview_lines.append((labels["target_users"], target_users))
    else:
        overview_lines.append((labels["target_users"], "Not specified"))
    mode_labels = {"screenshots": "Screenshots", "urls": "URLs", "hybrid": "Hybrid"}
    overview_lines.append((labels["mode"], mode_labels.get(mode, mode)))
    if tally:
        from audit_engine import tally_string
        overview_lines.append((labels["severity_tally"], tally_string(tally, language)))
    if benchmark != "none":
        bench_labels = {"market": "Market", "competitors": "Competitors", "both": "Market + Competitors"}
        overview_lines.append((labels["benchmark_scope"], bench_labels.get(benchmark, benchmark)))
    try:
        set_body_lines(slide, PH_BODY_CONTENT, overview_lines)
    except RuntimeError:
        # Fallback: try body idx 1
        try:
            set_body_lines(slide, PH_BODY_PICTURE, overview_lines)
        except RuntimeError:
            pass
    _progress("Overview")

    # --- 3–4. Section dividers + findings ---
    for sev_key, section_label_key in SEVERITY_SECTION_KEYS:
        sev_findings = [f for f in findings if f["severity"] == sev_key]
        if not sev_findings:
            continue

        # Section divider
        slide = add_slide(prs, LAYOUT_SECTION)
        set_title(slide, labels[section_label_key])
        for ph in slide.placeholders:
            if ph.placeholder_format.idx == PH_SUBTITLE:
                ph.text = labels["findings_count"].format(n=len(sev_findings))
                break
        _progress(labels[section_label_key])

        # Individual finding slides
        for f in sev_findings:
            # Determine if we have a matching screenshot
            shot_name = _extract_screenshot_name(f.get("evidence", ""))
            shot_data = _find_screenshot(shot_name, screenshots) if shot_name else None

            if shot_data:
                slide = add_slide(prs, LAYOUT_PICTURE)
                # Save screenshot to temp file for insertion
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp.write(shot_data)
                    tmp_path = tmp.name
                try:
                    insert_image_fit(slide, PH_PICTURE, tmp_path)
                finally:
                    os.unlink(tmp_path)
                body_ph_idx = PH_BODY_PICTURE
            else:
                slide = add_slide(prs, LAYOUT_CONTENT)
                body_ph_idx = PH_BODY_CONTENT

            # Title: severity + short title (capped at 36 chars)
            title_text = f"#{f['severity_raw']} — {f['title']}"
            if len(title_text) > 36:
                title_text = title_text[:33] + "…"
            set_title(slide, title_text)

            # Body: finding text + suggestions/solution + heuristic
            body_lines = _format_finding_body(f, labels)
            try:
                set_body_lines(slide, body_ph_idx, body_lines)
            except RuntimeError:
                # Try alternate placeholder
                alt_idx = PH_BODY_CONTENT if body_ph_idx == PH_BODY_PICTURE else PH_BODY_PICTURE
                try:
                    set_body_lines(slide, alt_idx, body_lines)
                except RuntimeError:
                    pass

            _progress(f['title'][:30])

    # --- 5. Benchmark section ---
    if benchmark != "none" and benchmark_text:
        slide = add_slide(prs, LAYOUT_SECTION)
        set_title(slide, labels.get("benchmarks", "Benchmarks"))
        _progress("Benchmark divider")

        slide = add_slide(prs, LAYOUT_CONTENT)
        bench_title = labels.get(
            "market_benchmark" if benchmark == "market" else "competitor_benchmark",
            "Benchmarks"
        )
        set_title(slide, bench_title)
        # Truncate benchmark text for slide body (max ~200 words)
        bench_body = _truncate_for_slide(benchmark_text, 200)
        try:
            set_body_lines(slide, PH_BODY_CONTENT, [bench_body])
        except RuntimeError:
            try:
                set_body_lines(slide, PH_BODY_PICTURE, [bench_body])
            except RuntimeError:
                pass
        _progress("Benchmark content")

    # --- 6. Closing slide ---
    try:
        slide = add_slide(prs, LAYOUT_CLOSING)
        for ph in slide.placeholders:
            if ph.placeholder_format.idx == PH_BODY_CONTENT:
                ph.text_frame.text = labels["closing_body"]
                break
    except Exception:
        # Fallback to content slide
        slide = add_slide(prs, LAYOUT_CONTENT)
        set_title(slide, labels["closing"])
        try:
            set_body_lines(slide, PH_BODY_CONTENT, [labels["closing_body"]])
        except RuntimeError:
            pass
    _progress("Closing")

    # Save to bytes
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp_raw:
        prs.save(tmp_raw.name)
        raw_path = tmp_raw.name

    # Dedup zip
    deduped_path = raw_path.replace(".pptx", "_clean.pptx")
    dedup_zip(raw_path, deduped_path)

    with open(deduped_path, "rb") as f:
        result = f.read()

    # Cleanup
    os.unlink(raw_path)
    os.unlink(deduped_path)

    return result


def _extract_screenshot_name(evidence: str) -> str | None:
    """Extract screenshot filename from evidence reference text."""
    if not evidence:
        return None
    # Match patterns like "Screenshot 2 — home.png" or "screenshot home.png"
    match = re.search(r"[Ss]creenshot\s*\d*\s*[—–-]?\s*(\S+\.(?:png|jpg|jpeg|webp))", evidence)
    if match:
        return match.group(1)
    # Match just a filename
    match = re.search(r"(\S+\.(?:png|jpg|jpeg|webp))", evidence)
    if match:
        return match.group(1)
    return None


def _find_screenshot(name: str, screenshots: dict[str, bytes]) -> bytes | None:
    """Find a screenshot by name, with fuzzy matching."""
    if not name or not screenshots:
        return None
    # Exact match
    if name in screenshots:
        return screenshots[name]
    # Case-insensitive
    name_lower = name.lower()
    for k, v in screenshots.items():
        if k.lower() == name_lower:
            return v
    # Partial match
    for k, v in screenshots.items():
        if name_lower in k.lower() or k.lower() in name_lower:
            return v
    return None


def _format_finding_body(finding: dict, labels: dict) -> list:
    """Format finding dict into body lines for set_body_lines."""
    lines = []

    # Main finding text — extract from the full body, truncate for slide
    body_text = finding.get("body", "")
    # Try to extract just the "Finding:" section
    finding_match = re.search(
        r"\*\*(?:Finding|Tespit|Befund)\s*:?\*\*\s*(.+?)(?=\n\*\*|\Z)",
        body_text, re.DOTALL
    )
    if finding_match:
        main_text = finding_match.group(1).strip()
    else:
        # Use first paragraph of body
        paragraphs = body_text.strip().split("\n\n")
        main_text = paragraphs[0] if paragraphs else body_text

    main_text = _truncate_for_slide(main_text, 120)
    lines.append((labels.get("finding", "Finding"), main_text))

    # Suggestions or Solution
    sugg_match = re.search(
        r"\*\*(?:Suggestions|Öneriler|Vorschläge|Solution|Çözüm|Lösung)\s*:?\*\*\s*(.+?)(?=\n\*\*|\Z)",
        body_text, re.DOTALL
    )
    if sugg_match:
        sugg_text = _truncate_for_slide(sugg_match.group(1).strip(), 80)
        label_key = "solution" if "Solution" in sugg_match.group(0) or "Çözüm" in sugg_match.group(0) or "Lösung" in sugg_match.group(0) else "suggestions"
        lines.append((labels.get(label_key, "Suggestions"), sugg_text))

    # Heuristic
    if finding.get("heuristic"):
        heur_text = _truncate_for_slide(finding["heuristic"], 50)
        lines.append((labels.get("heuristic", "Heuristic"), heur_text))

    return lines


def _truncate_for_slide(text: str, max_words: int) -> str:
    """Truncate text to approximately max_words words."""
    # Clean markdown formatting
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)  # italic
    text = re.sub(r"^-\s+", "• ", text, flags=re.MULTILINE)  # bullets
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)  # numbered lists

    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "…"

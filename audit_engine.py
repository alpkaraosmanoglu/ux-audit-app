"""Audit engine — constructs the system prompt from the ux-audit skill methodology
and streams findings from the Claude API.

BYOK: the Anthropic API key is passed per-call from session state. Never stored.

Reference material is loaded from the vendored skill bundle at
skills/ux-audit-skill/references/ — this repo's existing convention.
"""

import base64
import pathlib
import re

import anthropic

REFERENCES_DIR = pathlib.Path(__file__).parent / "skills" / "ux-audit-skill" / "references"

DEFAULT_MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Reference material (loaded once, embedded in the system prompt)
# ---------------------------------------------------------------------------

def _load_ref(name: str) -> str:
    return (REFERENCES_DIR / name).read_text(encoding="utf-8")


def _frameworks() -> str:
    return _load_ref("frameworks.md")


def _language_labels() -> str:
    return _load_ref("language_labels.md")


def _calibration_examples() -> str:
    return _load_ref("calibration_examples.md")


# ---------------------------------------------------------------------------
# System prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """\
You are a senior UX auditor producing a structured UX audit in the methodology \
of Başak Akbulak. You ground findings in cognitive and behavioral principles, \
structure them around specific observations with severity tags, and optionally \
include market and competitor benchmarking.

## Language
Produce the entire audit in {language}. All labels, severity tags, framework \
citations, and section headers must be in {language}.

## Language labels
{language_labels}

## Mode
The audit mode is **{mode}**.
{mode_rules}

## Frameworks — grounding library
{frameworks}

## Calibration — example findings
Study these examples carefully. They set the bar for structure, tone, and depth.
{calibration}

## Method — two-pass walkthrough
Analyze in two modes:
1. **Novice pass** — encounter the product as a first-time user. What feels off, \
where friction appears, where the eye gets lost.
2. **Expert pass** — apply frameworks. Name what you noticed, attach diagnoses, \
cite the principle that explains why the issue matters.

## Severity tagging
Use these severity levels (in {language}):
- **Major** — blocks or seriously degrades the primary user task
- **Mid** — creates noticeable friction but doesn't prevent task completion
- **Minor** — cosmetic or minor ergonomic issue
- **Open question** — needs stakeholder input rather than a fix

## Finding structure
Each finding must contain:
1. **Severity tag** (language-appropriate)
2. **Short finding title** — ≤36 chars total including the tag. Hard limit.
3. **Finding** — 1–2 paragraphs. Describe the user's likely experience.
4. **Heuristic** (optional, encouraged where it strengthens the finding)
5. **Solution or Suggestions** — Solution when there's a clear right answer; \
Suggestions (I, II, III) when 2–3 legitimate paths exist with different trade-offs.
6. **Evidence reference** — which screenshot or URL the finding relates to.

## Constraints
- NEVER invent details not in the evidence.
- NEVER generate generic findings. Every finding must be specific.
- Don't pad. 5 tight findings > 15 padded ones.
- Paraphrase, don't quote competitor examples.
- Citation is encouraged but not required — cite when it genuinely explains user behavior.

## Output format
Produce the audit as Markdown with these sections:
1. **Cover** — product name, pages reviewed, target users (or not-specified note), \
severity tally, mode indicator{benchmark_cover}
2. **Findings** — ordered Major → Mid → Minor → Open questions
{benchmark_section}
Format each finding with a clear heading: `### [severity tag] — [short title]`

{product_context}
{benchmark_instructions}
"""

MODE_RULES = {
    "screenshots": (
        "Visual audit (screenshots). Covers visual hierarchy, layout, attention flow, "
        "and interaction patterns. Full framework library available. Findings must be "
        "grounded in what is visible in the provided screenshots."
    ),
    "urls": (
        "Structural audit (URLs). Covers IA, content hierarchy, copy, link structure. "
        "Visual hierarchy and interaction issues are out of scope. Do NOT reference "
        "visual design, color, weight, or attention flow — you cannot see those."
    ),
    "hybrid": (
        "Combined (URLs + screenshots). Covers structural and visual analysis together. "
        "Findings are strongest when structural and visual evidence disagree."
    ),
}

BENCHMARK_INSTRUCTIONS = {
    "none": "",
    "market": (
        "## Benchmarking — Market\n"
        "After findings, add a Market Benchmark section. Describe 3–5 dominant patterns "
        "in the product's sector. For each: name the pattern, assign a Kano tier "
        "(basic / performance / delight), compare to the audited product."
    ),
    "competitors": (
        "## Benchmarking — Competitors\n"
        "After findings, add a Competitor Benchmark section. For each competitor: "
        "what they do, 2–4 notable UX patterns with Kano tiers, comparison to the "
        "audited product. End with a 'What to steal, what to ignore' paragraph."
    ),
    "both": (
        "## Benchmarking — Market + Competitors\n"
        "After findings, add: (1) Market section — 3–5 sector patterns with Kano tiers. "
        "(2) Competitor section — per-competitor analysis. (3) Synthesis paragraph: "
        "which competitor patterns are broad market moves vs. unique differentiators. "
        "End with 'What to steal, what to ignore'."
    ),
}


def build_system_prompt(
    language: str,
    mode: str,
    benchmark: str,
    product_name: str,
    client_name: str = "",
    industry: str = "",
    target_users: str = "",
    audience: str = "",
    scope_notes: str = "",
    competitor_names: list[str] | None = None,
) -> str:
    """Assemble the full system prompt from skill methodology + user config."""
    ctx_lines = [f"## Product context\n- **Product name:** {product_name}"]
    if client_name:
        ctx_lines.append(f"- **Client:** {client_name}")
    if industry:
        ctx_lines.append(f"- **Industry:** {industry}")
    if target_users:
        ctx_lines.append(f"- **Target users:** {target_users}")
    else:
        ctx_lines.append(
            '- **Target users:** Not specified. Add this note in the cover: '
            '"Target users were not specified. Findings are based on inference."'
        )
    if audience:
        ctx_lines.append(f"- **Audit audience:** {audience}")
    if scope_notes:
        ctx_lines.append(f"- **Scope notes:** {scope_notes}")
    if competitor_names:
        ctx_lines.append(f"- **Named competitors:** {', '.join(competitor_names)}")
    product_context = "\n".join(ctx_lines)

    benchmark_cover = ", benchmark scope" if benchmark != "none" else ""
    benchmark_section = (
        "3. **Benchmarking** — as instructed below\n" if benchmark != "none" else ""
    )

    return SYSTEM_PROMPT_TEMPLATE.format(
        language=language,
        language_labels=_language_labels(),
        mode=mode.capitalize(),
        mode_rules=MODE_RULES.get(mode, MODE_RULES["screenshots"]),
        frameworks=_frameworks(),
        calibration=_calibration_examples(),
        benchmark_cover=benchmark_cover,
        benchmark_section=benchmark_section,
        product_context=product_context,
        benchmark_instructions=BENCHMARK_INSTRUCTIONS.get(benchmark, ""),
    )


# ---------------------------------------------------------------------------
# User message construction
# ---------------------------------------------------------------------------

def build_user_message(
    mode: str,
    screenshots: list[dict] | None = None,
    urls: list[str] | None = None,
) -> list[dict]:
    """Build the user message content array with text and images.

    Args:
        mode: 'screenshots', 'urls', or 'hybrid'
        screenshots: list of dicts with 'name', 'data' (bytes), 'mime_type'
        urls: list of URL strings
    """
    content = []

    if mode in ("screenshots", "hybrid") and screenshots:
        content.append({
            "type": "text",
            "text": (
                f"I'm providing {len(screenshots)} screenshot(s) of the product. "
                "Please analyze each one thoroughly."
            ),
        })
        for i, shot in enumerate(screenshots, 1):
            b64 = base64.standard_b64encode(shot["data"]).decode("ascii")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": shot["mime_type"],
                    "data": b64,
                },
            })
            content.append({
                "type": "text",
                "text": f"Screenshot {i} — {shot['name']}",
            })

    if mode in ("urls", "hybrid") and urls:
        url_list = "\n".join(f"- {u}" for u in urls)
        content.append({
            "type": "text",
            "text": f"URLs to analyze:\n{url_list}",
        })

    if not content:
        content.append({
            "type": "text",
            "text": "Please produce the UX audit based on the context provided.",
        })

    content.append({
        "type": "text",
        "text": "Now produce the complete UX audit. Follow the finding structure exactly.",
    })

    return content


# ---------------------------------------------------------------------------
# Streaming API call
# ---------------------------------------------------------------------------

def stream_audit(
    api_key: str,
    system_prompt: str,
    user_message: list[dict],
    model: str = DEFAULT_MODEL,
):
    """Stream the audit generation, yielding text chunks.

    Yields (event_type, data) tuples:
        ('text', str)       — a chunk of response text
        ('done', str)       — the full response text
        ('error', str)      — error message
    """
    client = anthropic.Anthropic(api_key=api_key)

    try:
        with client.messages.stream(
            model=model,
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            full_text = ""
            for text in stream.text_stream:
                full_text += text
                yield ("text", text)
            yield ("done", full_text)
    except anthropic.AuthenticationError:
        yield ("error", "Invalid API key. Please check your key and try again.")
    except anthropic.RateLimitError:
        yield ("error", "Rate limit exceeded. Please wait a moment and try again.")
    except anthropic.APIError as e:
        yield ("error", f"API error: {e.message}")
    except Exception as e:
        yield ("error", f"Unexpected error: {str(e)}")


# ---------------------------------------------------------------------------
# Parse findings from Markdown output
# ---------------------------------------------------------------------------

def parse_findings(audit_md: str) -> list[dict]:
    """Extract structured findings from the audit Markdown.

    Returns list of dicts with keys:
        severity, title, body, heuristic, suggestions, evidence, full_text
    """
    findings = []
    pattern = r"###\s+(?:#)?(Major|Mid|Minor|Önemli|Orta|Hafif|Wichtig|Mittel|Gering|Open question|Açık soru|Offene Frage)\s*[—–-]\s*(.+)"
    parts = re.split(r"(?=###\s+)", audit_md)

    for part in parts:
        match = re.match(pattern, part.strip(), re.IGNORECASE)
        if not match:
            continue
        severity_raw = match.group(1).strip()
        title = match.group(2).strip()
        body = part[match.end():].strip()

        sev_map = {
            "major": "major", "önemli": "major", "wichtig": "major",
            "mid": "mid", "orta": "mid", "mittel": "mid",
            "minor": "minor", "hafif": "minor", "gering": "minor",
            "open question": "open", "açık soru": "open", "offene frage": "open",
        }
        severity = sev_map.get(severity_raw.lower(), "mid")

        heuristic = ""
        heur_match = re.search(
            r"\*\*(?:Heuristic|Sezgisel kural|Heuristik)\s*:?\*\*\s*(.+?)(?:\n\n|\n\*\*|\Z)",
            body, re.DOTALL
        )
        if heur_match:
            heuristic = heur_match.group(1).strip()

        evidence = ""
        ev_match = re.search(
            r"\*\*(?:Evidence reference|Kanıt referansı|Beleg)\s*:?\*\*\s*(.+?)(?:\n\n|\n\*\*|\Z)",
            body, re.DOTALL
        )
        if ev_match:
            evidence = ev_match.group(1).strip()

        findings.append({
            "severity": severity,
            "severity_raw": severity_raw,
            "title": title,
            "body": body,
            "heuristic": heuristic,
            "evidence": evidence,
            "full_text": part.strip(),
        })

    return findings


def severity_tally(findings: list[dict]) -> dict[str, int]:
    """Count findings by severity."""
    tally = {"major": 0, "mid": 0, "minor": 0, "open": 0}
    for f in findings:
        sev = f.get("severity", "mid")
        if sev in tally:
            tally[sev] += 1
    return tally


def tally_string(tally: dict[str, int], language: str = "English") -> str:
    """Format the tally as a human-readable string."""
    total = sum(tally.values())
    labels = {
        "English": {"major": "Major", "mid": "Mid", "minor": "Minor", "open": "Open question"},
        "Türkçe": {"major": "Önemli", "mid": "Orta", "minor": "Hafif", "open": "Açık soru"},
        "Deutsch": {"major": "Wichtig", "mid": "Mittel", "minor": "Gering", "open": "Offene Frage"},
    }
    l = labels.get(language, labels["English"])
    parts = []
    for sev in ("major", "mid", "minor", "open"):
        if tally[sev] > 0:
            parts.append(f"{tally[sev]} {l[sev]}")
    return f"{total} findings" + (" · " + " · ".join(parts) if parts else "")

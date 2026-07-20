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
6. **Evidence reference** — which screenshot or URL the finding relates to. \
In screenshots/hybrid mode, cite the EXACT numbered label given to you, in the \
format "Screenshot N" (e.g. "Screenshot 2") — do not paraphrase or invent a \
filename. In URLs mode, cite the exact URL analyzed. This reference is used to \
programmatically attach the correct image to the finding, so precision here matters.

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
        "After findings, add a Competitor Benchmark section. Ground this ENTIRELY in "
        "the competitor screenshots and/or URLs provided to you below — do not invent "
        "or assume features you weren't shown. For each competitor: what they do, "
        "2–4 notable UX patterns actually visible in the provided evidence with Kano "
        "tiers, comparison to the audited product. If no competitor evidence (screenshots "
        "or URLs) was provided for a named competitor, say so explicitly rather than "
        "fabricating analysis. End with a 'What to steal, what to ignore' paragraph."
    ),
    "both": (
        "## Benchmarking — Market + Competitors\n"
        "After findings, add: (1) Market section — 3–5 sector patterns with Kano tiers. "
        "(2) Competitor section — per-competitor analysis grounded ENTIRELY in the "
        "competitor screenshots and/or URLs provided below (do not invent features you "
        "weren't shown — say so explicitly if no evidence was provided for a named "
        "competitor). (3) Synthesis paragraph: which competitor patterns are broad "
        "market moves vs. unique differentiators. End with 'What to steal, what to ignore'."
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
    market_sector: str = "",
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
    if market_sector:
        ctx_lines.append(f"- **Market/sector to benchmark against:** {market_sector}")
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
    competitors: list[dict] | None = None,
    comp_screenshots: dict[int, list[dict]] | None = None,
) -> list[dict]:
    """Build the user message content array with text and images.

    Args:
        mode: 'screenshots', 'urls', or 'hybrid'
        screenshots: list of dicts with 'name', 'data' (bytes), 'mime_type'
        urls: list of URL strings
        competitors: list of dicts with 'name', 'url' — the benchmarking targets
        comp_screenshots: dict mapping competitor index (0-based, matching the
            `competitors` list) to a list of screenshot dicts for that competitor
    """
    content = []

    if mode in ("screenshots", "hybrid") and screenshots:
        content.append({
            "type": "text",
            "text": (
                f"I'm providing {len(screenshots)} screenshot(s) of the product. "
                "Please analyze each one thoroughly. When you cite evidence, use "
                "the exact label 'Screenshot N' shown before each image below."
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

    # Competitor benchmarking evidence — screenshots and/or URLs per competitor.
    # Without this, competitor benchmarking sections are ungrounded guesses.
    if competitors:
        has_any_evidence = bool(comp_screenshots) or any(c.get("url") for c in competitors)
        content.append({
            "type": "text",
            "text": (
                "Competitor benchmarking evidence follows. Ground the Competitor "
                "Benchmark section entirely in what's provided here — screenshots "
                "and/or URLs per competitor. If a named competitor has no evidence "
                "below, say so explicitly rather than inventing analysis."
                if has_any_evidence else
                "The following competitors were named, but no screenshots or URLs "
                "were provided for them. Say so explicitly in the Competitor "
                "Benchmark section rather than inventing analysis of their product."
            ),
        })
        for idx, comp in enumerate(competitors):
            name = comp.get("name") or f"Competitor {idx + 1}"
            url = comp.get("url", "")
            label = f"Competitor: {name}" + (f" — {url}" if url else "")
            content.append({"type": "text", "text": label})

            shots = (comp_screenshots or {}).get(idx, [])
            for shot in shots:
                b64 = base64.standard_b64encode(shot["data"]).decode("ascii")
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": shot.get("mime_type", "image/png"),
                        "data": b64,
                    },
                })
                content.append({
                    "type": "text",
                    "text": f"({name} screenshot — {shot['name']})",
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

        # Reliable screenshot lookup: the prompt instructs the model to cite
        # "Screenshot N" exactly, so prefer this numeric index over fuzzy
        # filename matching (which breaks whenever the model paraphrases).
        screenshot_index = None
        idx_match = re.search(r"[Ss]creenshot\s+(\d+)", evidence)
        if idx_match:
            screenshot_index = int(idx_match.group(1))

        findings.append({
            "severity": severity,
            "severity_raw": severity_raw,
            "title": title,
            "body": body,
            "heuristic": heuristic,
            "evidence": evidence,
            "screenshot_index": screenshot_index,
            "full_text": part.strip(),
        })

    return findings


def split_header(audit_md: str) -> str:
    """Return the portion of the audit Markdown before the first finding heading.

    Used to preserve the cover/overview section when findings are edited and
    the audit text needs to be reassembled.
    """
    match = re.search(r"###\s+", audit_md)
    return audit_md[: match.start()].rstrip() if match else audit_md.rstrip()


def render_finding_markdown(finding: dict) -> str:
    """Render a single finding dict back into its Markdown block."""
    return f"### {finding['severity_raw']} — {finding['title']}\n\n{finding['body']}".rstrip()


def compose_audit_markdown(header: str, findings: list[dict]) -> str:
    """Reassemble the full audit Markdown from a header and an (edited) findings list."""
    parts = [header] if header else []
    parts.extend(render_finding_markdown(f) for f in findings)
    return "\n\n".join(p for p in parts if p).strip() + "\n"


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

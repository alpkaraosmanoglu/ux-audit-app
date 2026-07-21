"""UX Audit Studio — Streamlit app.

Turn screenshots into a client-ready UX audit with severity tags, framework
citations, and a matching .pptx deck. BYOK: user provides their own Anthropic
API key (session-only, never stored).

Design reference: Claude Design mockup (UX Audit Studio.dc.html)
Methodology:     ux-audit-skill (written audit) + ux-audit-deck-skill (deck)
"""

import io
import re
import time
import zipfile
from datetime import datetime

import streamlit as st

from styles import CUSTOM_CSS
from audit_engine import (
    VERIFICATION_TAG_RE,
    build_system_prompt,
    build_user_message,
    compose_audit_markdown,
    condense_for_deck,
    extract_benchmark_section,
    parse_findings,
    severity_tally,
    split_header,
    stream_audit,
    tally_string,
)
from deck_engine import generate_deck
from pdf_engine import generate_audit_pdf

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="UX Audit Studio",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
DEFAULTS = {
    "step": "home",
    "api_key": "",
    "key_touched": False,
    "language": ["English"],
    "mode": "screenshots",
    "product_name": "",
    "client_name": "",
    "industry": "",
    "target_users": "",
    "audience": "",
    "scope_notes": "",
    "urls_text": "",
    "benchmark": "none",
    "market_sector": "",
    "competitors": [{"name": "", "url": ""}],
    "screenshots": [],       # list of {"name": str, "data": bytes, "mime_type": str}
    "comp_screenshots": {},   # comp_idx -> list of {"name", "data", "mime_type"}
    "audits": {},            # language -> {"text", "header", "findings", "tally"}
    "active_language": "",   # which language's audit is currently shown/edited
    "regenerate_language": None,  # set by "Regenerate" to redo just one language
    "edit_mode": False,
    "decks": {},             # language -> pptx bytes
    "generating": False,
    "deck_generating": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def go(step: str):
    st.session_state.step = step


def current_audit() -> dict:
    """The active language's working audit state (header/text/findings/tally).
    Findings is the same list object stored in session_state.audits, so
    in-place edits (severity/title/body changes, add/delete) persist
    automatically without an explicit save step.
    """
    lang = st.session_state.active_language
    if lang not in st.session_state.audits:
        st.session_state.audits[lang] = {"text": "", "header": "", "findings": [], "tally": {}}
    return st.session_state.audits[lang]


_VERIF_BADGES = {
    "Verified": ("verif-verified", "✓ Verified"),
    "Unverified": ("verif-unverified", "? Unverified"),
    "Outdated?": ("verif-outdated", "⚠ Possibly outdated"),
}


def render_benchmark_panel(audit_text: str):
    """Render the audit's benchmark section (if any) as its own styled panel,
    converting inline [Verified]/[Unverified]/[Outdated?] tags from the model
    into colored badges so the user can see at a glance which benchmark claims
    were confirmed via web search vs. drafted from training knowledge alone.
    """
    section = extract_benchmark_section(audit_text)
    if not section:
        return

    def _sub(m):
        cls, label = _VERIF_BADGES[m.group(1)]
        return f'<span class="verif-tag {cls}">{label}</span>'

    body_html = VERIFICATION_TAG_RE.sub(_sub, section)

    with st.container(border=True):
        st.markdown(
            '<div class="benchmark-legend">'
            '<span class="verif-tag verif-verified">✓ Verified</span>&nbsp;confirmed via web search&nbsp;&nbsp;·&nbsp;&nbsp;'
            '<span class="verif-tag verif-unverified">? Unverified</span>&nbsp;drafted from training knowledge, not confirmed&nbsp;&nbsp;·&nbsp;&nbsp;'
            '<span class="verif-tag verif-outdated">⚠ Possibly outdated</span>&nbsp;search suggests this may have changed'
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(body_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Top navigation bar
# ---------------------------------------------------------------------------
STEPS = [
    ("home", "Home"),
    ("setup", "Setup"),
    ("config", "Configure"),
    ("generating", "Generating"),
    ("audit", "Audit"),
    ("deck", "Deck"),
]

nav_html = '<div class="topnav-bar"><span class="brand">AUDIT STUDIO</span>'
for key, label in STEPS:
    active = "active" if st.session_state.step == key or (
        key == "deck" and st.session_state.step in ("deck_generating", "deck_ready")
    ) else ""
    nav_html += f'<span class="navlink {active}">{label}</span>'
nav_html += "</div>"
st.markdown(nav_html, unsafe_allow_html=True)


# =========================================================================
# STEP 1 — Home
# =========================================================================
if st.session_state.step == "home":
    st.markdown('<div class="screen-kicker">Step 1 of 6 — Arrival</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-title">Turn screenshots into a client-ready audit</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="hero-sub">Upload 4–8 product screenshots, answer a few setup '
        "questions, and get a structured UX audit with severity tags, framework "
        "citations, and a matching deck.</div>",
        unsafe_allow_html=True,
    )

    if st.button("Start audit →", type="primary"):
        go("setup")
        st.rerun()

    st.markdown(
        '<div class="byok-notice">'
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">'
        '<rect x="5" y="11" width="14" height="9" rx="0"></rect>'
        '<path d="M8 11V7a4 4 0 0 1 8 0v4"></path></svg>'
        " Bring your own Anthropic API key — session-only, never stored.</div>",
        unsafe_allow_html=True,
    )


# =========================================================================
# STEP 2 — Setup (API key)
# =========================================================================
elif st.session_state.step == "setup":
    st.markdown('<div class="screen-kicker">Step 2 of 6 — Setup</div>', unsafe_allow_html=True)
    st.markdown("## Add your API key")
    st.markdown(
        "The audit runs on Claude, using your own Anthropic key. It stays in your "
        "browser for this session only — we never send it anywhere else or write it to disk.",
    )

    with st.container(border=True):
        st.markdown("#### Connect your Anthropic key")

        api_key = st.text_input(
            "Anthropic API key",
            value=st.session_state.api_key,
            type="password",
            help="Stored only in this browser session. Cleared when you close the tab.",
        )
        st.session_state.api_key = api_key

        key_valid = api_key.startswith("sk-ant-") if api_key else False

        if key_valid:
            st.markdown('<span class="key-valid-check">✓ Key format valid</span>', unsafe_allow_html=True)

        st.caption(
            "Stored only in this browser session. Cleared when you close the tab. "
            "[Find your key in the Anthropic Console →](https://console.anthropic.com/settings/keys)"
        )

        if st.session_state.key_touched and not key_valid:
            st.error(
                '**Invalid key.** Anthropic keys start with "sk-ant-" — '
                "double-check you copied the whole string. "
                "[Get a key from the Anthropic Console →](https://console.anthropic.com/settings/keys)"
            )

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Cancel"):
                go("home")
                st.rerun()
        with col2:
            if st.button("Continue", type="primary"):
                st.session_state.key_touched = True
                if key_valid:
                    go("config")
                    st.rerun()
                else:
                    st.rerun()


# =========================================================================
# STEP 3 — Configuration
# =========================================================================
elif st.session_state.step == "config":
    st.markdown('<div class="screen-kicker">Step 3 of 6 — Configuration</div>', unsafe_allow_html=True)
    st.markdown("## Set up the audit")

    # --- Language ---
    st.markdown("---")
    st.markdown('<span class="section-label">Language</span>', unsafe_allow_html=True)
    lang_options = ["English", "Türkçe", "Deutsch"]
    selected_langs = st.multiselect(
        "Select languages (audit + deck produced in each)",
        options=lang_options,
        default=st.session_state.language,
        label_visibility="collapsed",
    )
    st.session_state.language = selected_langs if selected_langs else st.session_state.language
    st.caption("Select more than one — the audit and deck will be produced in every language you choose.")
    if not selected_langs:
        st.error("Select at least one language to continue.")

    # --- Mode ---
    st.markdown("---")
    st.markdown('<span class="section-label">Mode</span>', unsafe_allow_html=True)

    mode_cols = st.columns(3)
    modes = [
        {
            "key": "screenshots",
            "title": "Screenshots",
            "pros": ["Full visual fidelity — sees layout, color, hierarchy",
                     "Best for interaction & usability findings"],
            "cons": ["Needs 4–8 prepared images upfront"],
        },
        {
            "key": "urls",
            "title": "URLs only",
            "pros": ["No prep — just paste links",
                     "Good for content & IA review"],
            "cons": ["Can't see visual design or styling",
                     "Blocked by logins or paywalls"],
        },
        {
            "key": "hybrid",
            "title": "Hybrid",
            "pros": ["Screenshots plus supporting URLs",
                     "Most complete context"],
            "cons": ["Most setup work of the three"],
        },
    ]
    for col, m in zip(mode_cols, modes):
        with col:
            selected = st.session_state.mode == m["key"]
            border_style = "border: 2px solid #6f5cf6; background: rgba(111,92,246,0.06);" if selected else "border: 2px solid #e4e4e7;"
            badge = '<span class="mode-badge">Selected</span>' if selected else ""

            pros_html = "".join(f'<div class="pro-item">+ {p}</div>' for p in m["pros"])
            cons_html = "".join(f'<div class="con-item">– {c}</div>' for c in m["cons"])

            st.markdown(
                f'<div style="{border_style} padding: 16px; height: 100%;">'
                f'{badge}'
                f'<h4 style="margin: 0 0 8px 0; font-size: 15px;">{m["title"]}</h4>'
                f'{pros_html}{cons_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f'Select {m["title"]}', key=f'mode_{m["key"]}',
                         type="primary" if selected else "secondary",
                         use_container_width=True):
                st.session_state.mode = m["key"]
                st.rerun()

    # --- Product context ---
    st.markdown("---")
    st.markdown('<span class="section-label">Product context</span>', unsafe_allow_html=True)

    ctx_cols = st.columns(2)
    with ctx_cols[0]:
        st.session_state.product_name = st.text_input(
            "Product name", value=st.session_state.product_name,
            placeholder="e.g. Marlow",
        )
    with ctx_cols[1]:
        st.session_state.client_name = st.text_input(
            "Client name (optional)", value=st.session_state.client_name,
        )

    ctx_cols2 = st.columns(2)
    with ctx_cols2[0]:
        st.session_state.industry = st.text_input(
            "Industry", value=st.session_state.industry,
            placeholder="e.g. Ecommerce, fintech, healthcare",
        )
    with ctx_cols2[1]:
        st.session_state.target_users = st.text_input(
            "Target users (optional)", value=st.session_state.target_users,
            placeholder="e.g. Time-pressed online shoppers, 25–45",
        )

    ctx_cols3 = st.columns(2)
    with ctx_cols3[0]:
        st.session_state.audience = st.text_input(
            "Audience for this audit (optional)", value=st.session_state.audience,
            placeholder="e.g. Client design team + stakeholders",
        )

    st.session_state.scope_notes = st.text_area(
        "Scope notes (optional)", value=st.session_state.scope_notes,
        placeholder="Anything specific to focus on — a flow, a recent redesign, known problem areas…",
    )

    # --- URLs (for urls / hybrid modes) ---
    if st.session_state.mode in ("urls", "hybrid"):
        st.markdown("---")
        st.markdown('<span class="section-label">Product URLs</span>', unsafe_allow_html=True)
        st.caption("Paste one URL per line — each becomes a screen in the audit.")
        st.session_state.urls_text = st.text_area(
            "URLs", value=st.session_state.urls_text,
            placeholder="https://example.com/\nhttps://example.com/pricing\nhttps://example.com/checkout",
            label_visibility="collapsed",
            height=140,
        )
        url_count = len([u for u in st.session_state.urls_text.split("\n") if u.strip()])
        st.caption(f"{url_count} URL{'s' if url_count != 1 else ''} added")

    # --- Screenshots (for screenshots / hybrid modes) ---
    if st.session_state.mode in ("screenshots", "hybrid"):
        st.markdown("---")
        st.markdown('<span class="section-label">Screenshots</span>', unsafe_allow_html=True)
        st.caption("Upload as many screenshots as you need. They'll appear as numbered evidence in the audit.")

        uploaded_files = st.file_uploader(
            "Upload screenshots",
            type=["png", "jpg", "jpeg", "webp"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if uploaded_files:
            new_shots = []
            for f in uploaded_files:
                data = f.read()
                mime = f.type or "image/png"
                new_shots.append({"name": f.name, "data": data, "mime_type": mime})
            st.session_state.screenshots = new_shots

        # Show thumbnails
        if st.session_state.screenshots:
            cols = st.columns(min(5, len(st.session_state.screenshots)))
            for i, shot in enumerate(st.session_state.screenshots):
                with cols[i % 5]:
                    st.image(shot["data"], caption=shot["name"], use_container_width=True)

    # --- Benchmarking ---
    st.markdown("---")
    st.markdown('<span class="section-label">Benchmarking</span>', unsafe_allow_html=True)

    bench_options = {"none": "None", "market": "Market", "competitors": "Competitors", "both": "Both"}
    bench_descriptions = {
        "none": "No benchmark context — the audit will focus on the product itself.",
        "market": "Benchmarks the product against standards and conventions typical of its industry.",
        "competitors": "Runs a deep-dive analysis of competitor products and features alongside your own.",
        "both": "Combines an industry benchmark with a deep-dive competitor analysis.",
    }

    bench_cols = st.columns(4)
    for col, (bkey, blabel) in zip(bench_cols, bench_options.items()):
        with col:
            if st.button(
                blabel,
                key=f"bench_{bkey}",
                type="primary" if st.session_state.benchmark == bkey else "secondary",
                use_container_width=True,
            ):
                st.session_state.benchmark = bkey
                st.rerun()

    st.markdown(
        f'<div class="bench-desc">{bench_descriptions[st.session_state.benchmark]}</div>',
        unsafe_allow_html=True,
    )

    # Market / sector field
    if st.session_state.benchmark in ("market", "both"):
        st.session_state.market_sector = st.text_input(
            "Market / sector to benchmark against",
            value=st.session_state.market_sector,
            placeholder="e.g. B2B pharmacy platforms, direct-to-consumer insurance, rural e-commerce",
            help="Used to ground the market benchmark section in the right conventions — leave blank to infer from industry.",
        )

    # Competitor fields
    if st.session_state.benchmark in ("competitors", "both"):
        st.markdown("---")
        st.caption(
            "Upload at least one screenshot or add a URL per competitor — without evidence, "
            "the audit can't ground the comparison and will say so rather than guessing."
        )
        for i, comp in enumerate(st.session_state.competitors):
            comp_cols = st.columns(2)
            with comp_cols[0]:
                comp["name"] = st.text_input(
                    f"Competitor {i+1} name (optional)",
                    value=comp.get("name", ""),
                    key=f"comp_name_{i}",
                    placeholder="e.g. Acme",
                )
            with comp_cols[1]:
                comp["url"] = st.text_input(
                    f"Competitor {i+1} URL (optional)",
                    value=comp.get("url", ""),
                    key=f"comp_url_{i}",
                    placeholder="https://competitor.com",
                )

            # Competitor screenshot upload
            comp_files = st.file_uploader(
                f"Competitor {i+1} screenshots (optional)",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key=f"comp_shots_{i}",
            )
            if comp_files:
                st.session_state.comp_screenshots[i] = [
                    {"name": f.name, "data": f.read(), "mime_type": f.type or "image/png"}
                    for f in comp_files
                ]

            if len(st.session_state.competitors) > 1:
                if st.button(f"Remove competitor {i+1}", key=f"rm_comp_{i}"):
                    st.session_state.competitors.pop(i)
                    st.rerun()

        if st.button("+ Add another competitor"):
            st.session_state.competitors.append({"name": "", "url": ""})
            st.rerun()

    # --- Generate button ---
    st.markdown("---")
    can_generate = bool(st.session_state.product_name) and bool(st.session_state.language)
    if st.session_state.mode in ("screenshots", "hybrid") and not st.session_state.screenshots:
        can_generate = False
    if st.session_state.mode in ("urls", "hybrid") and not st.session_state.urls_text.strip():
        if st.session_state.mode == "urls":
            can_generate = False

    if st.button("Generate audit →", type="primary", disabled=not can_generate):
        go("generating")
        st.rerun()

    if not can_generate:
        missing = []
        if not st.session_state.product_name:
            missing.append("product name")
        if st.session_state.mode in ("screenshots", "hybrid") and not st.session_state.screenshots:
            missing.append("screenshots")
        if st.session_state.mode == "urls" and not st.session_state.urls_text.strip():
            missing.append("URLs")
        if missing:
            st.caption(f"Required to continue: {', '.join(missing)}")


# =========================================================================
# STEP 4 — Generating
# =========================================================================
elif st.session_state.step == "generating":
    st.markdown('<div class="screen-kicker">Step 4 of 6 — Generation</div>', unsafe_allow_html=True)
    st.markdown("## Generating your audit…")

    # Regenerate re-does just one language; a fresh run does every selected language.
    langs_to_generate = (
        [st.session_state.regenerate_language]
        if st.session_state.regenerate_language
        else list(st.session_state.language)
    )

    mode = st.session_state.mode
    benchmark = st.session_state.benchmark

    competitor_names = [c["name"] for c in st.session_state.competitors if c.get("name")]
    active_competitors = st.session_state.competitors if benchmark in ("competitors", "both") else None

    urls = [u.strip() for u in st.session_state.urls_text.split("\n") if u.strip()] if st.session_state.urls_text else None

    # Evidence (screenshots/URLs/competitor material) doesn't depend on language.
    user_message = build_user_message(
        mode=mode,
        screenshots=st.session_state.screenshots if mode in ("screenshots", "hybrid") else None,
        urls=urls if mode in ("urls", "hybrid") else None,
        competitors=active_competitors,
        comp_screenshots=st.session_state.comp_screenshots if active_competitors else None,
    )

    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    findings_container = st.container()

    error_msg = None
    n_langs = len(langs_to_generate)

    for lang_i, language in enumerate(langs_to_generate):
        system_prompt = build_system_prompt(
            language=language,
            mode=mode,
            benchmark=benchmark,
            product_name=st.session_state.product_name,
            client_name=st.session_state.client_name,
            industry=st.session_state.industry,
            target_users=st.session_state.target_users,
            audience=st.session_state.audience,
            scope_notes=st.session_state.scope_notes,
            competitor_names=competitor_names if competitor_names else None,
            market_sector=st.session_state.market_sector if benchmark in ("market", "both") else "",
        )

        full_text = ""
        with findings_container:
            text_area = st.empty()
            for event_type, data in stream_audit(
                api_key=st.session_state.api_key,
                system_prompt=system_prompt,
                user_message=user_message,
                enable_web_search=(benchmark != "none"),
            ):
                if event_type == "text":
                    full_text += data
                    finding_count = full_text.count("###")
                    progress_val = min(0.95, (lang_i + min(0.9, finding_count * 0.15 + 0.1)) / n_langs)
                    progress_bar.progress(progress_val)
                    status_placeholder.markdown(
                        f'<div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#71717a;">'
                        f'<span class="spinner-dot"></span>'
                        f"Analyzing ({language})… {finding_count} finding(s) so far"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    text_area.markdown(full_text)
                elif event_type == "done":
                    full_text = data
                elif event_type == "error":
                    error_msg = data

        if error_msg:
            break

        findings = parse_findings(full_text)
        st.session_state.audits[language] = {
            "text": full_text,
            "header": split_header(full_text),
            "findings": findings,
            "tally": severity_tally(findings),
        }

    if error_msg:
        st.error(error_msg)
        if st.button("← Back to configuration"):
            go("config")
            st.rerun()
    else:
        progress_bar.progress(1.0)
        status_placeholder.markdown("**Generation complete.**")

        if st.session_state.regenerate_language:
            st.session_state.regenerate_language = None
        else:
            st.session_state.active_language = langs_to_generate[0]
        st.session_state.edit_mode = False

        time.sleep(0.5)
        go("audit")
        st.rerun()


# =========================================================================
# STEP 5 — Audit (review findings)
# =========================================================================
elif st.session_state.step == "audit":
    st.markdown('<div class="screen-kicker">Step 5 of 6 — Deliverable</div>', unsafe_allow_html=True)

    mode_labels = {"screenshots": "Screenshots", "urls": "URLs only", "hybrid": "Hybrid"}
    bench_labels = {"none": "No benchmarking", "market": "Market", "competitors": "Competitors", "both": "Market + Competitors"}

    available_langs = list(st.session_state.audits.keys())
    if st.session_state.active_language not in available_langs and available_langs:
        st.session_state.active_language = available_langs[0]
    language = st.session_state.active_language or (st.session_state.language[0] if st.session_state.language else "English")

    st.markdown(f"## UX Audit — {st.session_state.product_name}")

    if len(available_langs) > 1:
        chosen = st.radio(
            "Language",
            available_langs,
            index=available_langs.index(language),
            horizontal=True,
            label_visibility="collapsed",
            key="lang_switcher",
        )
        if chosen != st.session_state.active_language:
            st.session_state.active_language = chosen
            st.session_state.edit_mode = False
            st.rerun()
        language = chosen

    st.caption(
        f"{mode_labels.get(st.session_state.mode, st.session_state.mode)} mode · "
        f"{language} · "
        f"{bench_labels.get(st.session_state.benchmark, 'None')} · "
        f"Generated {datetime.now().strftime('%b %d, %Y')}"
    )

    cur = current_audit()
    findings = cur["findings"]
    tally = cur["tally"]
    lang_suffix = f"_{language.lower()}" if len(available_langs) > 1 else ""

    def resolve_screenshot(f: dict):
        """Look up a finding's screenshot. Prefers the reliable numeric
        screenshot_index (matches upload order) with a filename-based
        fallback for audits that were hand-edited or predate this field.
        """
        shots = st.session_state.screenshots
        idx = f.get("screenshot_index")
        if idx and 1 <= idx <= len(shots):
            return shots[idx - 1]["data"]
        ev = f.get("evidence", "")
        match = re.search(r"(\S+\.(?:png|jpg|jpeg|webp))", ev) if ev else None
        if match:
            shot_name = match.group(1).lower()
            for s in shots:
                if s["name"].lower() == shot_name or shot_name in s["name"].lower():
                    return s["data"]
        return None

    # --- Edit mode toggle ---
    top_cols = st.columns([3, 1])
    with top_cols[1]:
        edit_label = "Done editing" if st.session_state.edit_mode else "Edit findings"
        if st.button(edit_label, use_container_width=True):
            st.session_state.edit_mode = not st.session_state.edit_mode
            if not st.session_state.edit_mode:
                # Leaving edit mode: reassemble text + tally from the
                # (possibly edited) findings list.
                cur["text"] = compose_audit_markdown(cur["header"], cur["findings"])
                cur["tally"] = severity_tally(cur["findings"])
            st.rerun()

    if st.session_state.edit_mode:
        st.caption("Editing findings. Changes are kept locally until you download or generate a deck.")
        sev_options = ["MAJOR", "MID", "MINOR", "OPEN QUESTION"]
        for i, f in enumerate(findings):
            with st.container(border=True):
                ecols = st.columns([1, 3, 1])
                with ecols[0]:
                    current_sev = f["severity_raw"].upper()
                    sev_idx = sev_options.index(current_sev) if current_sev in sev_options else 1
                    new_sev = st.selectbox(
                        "Severity", sev_options, index=sev_idx, key=f"edit_sev_{i}", label_visibility="collapsed"
                    )
                    f["severity_raw"] = new_sev
                    f["severity"] = {"MAJOR": "major", "MID": "mid", "MINOR": "minor", "OPEN QUESTION": "open"}[new_sev]
                with ecols[1]:
                    f["title"] = st.text_input(
                        "Title", value=f["title"], key=f"edit_title_{i}", label_visibility="collapsed"
                    )
                with ecols[2]:
                    if st.button("Delete", key=f"edit_del_{i}", use_container_width=True):
                        findings.pop(i)
                        st.rerun()
                f["body"] = st.text_area(
                    "Body (Markdown)", value=f["body"], key=f"edit_body_{i}", height=140, label_visibility="collapsed"
                )
        if st.button("+ Add finding"):
            findings.append({
                "severity": "mid",
                "severity_raw": "MID",
                "title": "New finding",
                "body": "**Finding:** Describe the observation.\n\n**Solution:** Describe the fix.",
                "heuristic": "",
                "evidence": "",
                "screenshot_index": None,
                "full_text": "",
            })
            st.rerun()

    elif findings:
        for f in findings:
            sev_class = f"sev-{f['severity']}"
            shot_data = resolve_screenshot(f)

            col_img, col_text = st.columns([1, 4])
            with col_img:
                if shot_data:
                    st.image(shot_data, use_container_width=True)
                else:
                    st.markdown(
                        f'<div class="finding-shot">{f.get("evidence") or "—"}</div>',
                        unsafe_allow_html=True,
                    )
            with col_text:
                st.markdown(
                    f'<span class="sev-tag {sev_class}">{f["severity_raw"]}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown(f'<div class="finding-title">{f["title"]}</div>', unsafe_allow_html=True)

                # Render finding body as markdown
                body_clean = f["body"]
                # Remove the evidence reference line for cleaner display
                body_clean = re.sub(
                    r"\*\*(?:Evidence reference|Kanıt referansı|Beleg)\s*:?\*\*\s*.+?(?:\n|$)",
                    "", body_clean
                )
                st.markdown(body_clean)

                if f.get("heuristic"):
                    st.markdown(
                        f'<div class="finding-cite">{f["heuristic"]}</div>',
                        unsafe_allow_html=True,
                    )

            st.divider()
    else:
        # Fallback: show raw audit text
        st.markdown(cur["text"])

    # --- Benchmark section (shown separately since it's not part of the
    # per-finding structured list above) ---
    if st.session_state.benchmark != "none" and not st.session_state.edit_mode:
        st.markdown("### " + bench_labels.get(st.session_state.benchmark, "Benchmarks"))
        render_benchmark_panel(cur["text"])

    # --- Action bar ---
    st.markdown("---")
    tally_str = tally_string(tally, language) if tally else ""
    st.caption(tally_str)

    action_cols = st.columns([1, 1, 1, 1, 1])
    with action_cols[0]:
        if st.button("Regenerate", type="secondary"):
            st.session_state.regenerate_language = language
            go("generating")
            st.rerun()
    with action_cols[1]:
        pdf_bytes = generate_audit_pdf(
            product_name=st.session_state.product_name,
            language=language,
            mode=st.session_state.mode,
            benchmark=st.session_state.benchmark,
            findings=findings,
            tally=tally,
            screenshots=st.session_state.screenshots,
            audit_text=cur["text"],
        )
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"ux_audit_{st.session_state.product_name.lower().replace(' ', '_')}{lang_suffix}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with action_cols[2]:
        st.download_button(
            "Download .md",
            data=cur["text"],
            file_name=f"ux_audit_{st.session_state.product_name.lower().replace(' ', '_')}{lang_suffix}.md",
            mime="text/markdown",
        )
    with action_cols[3]:
        if st.button("Generate deck →", type="primary"):
            # Ensure any pending edits are folded into the working text before deck generation.
            cur["text"] = compose_audit_markdown(cur["header"], cur["findings"])
            cur["tally"] = severity_tally(cur["findings"])
            go("deck_generating")
            st.rerun()
    with action_cols[4]:
        if st.button("Start new audit"):
            for k, v in DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()


# =========================================================================
# STEP 6a — Deck generating
# =========================================================================
elif st.session_state.step == "deck_generating":
    st.markdown('<div class="screen-kicker">Step 6 of 6 — Deck</div>', unsafe_allow_html=True)
    st.markdown("## Generating your deck")

    langs = list(st.session_state.audits.keys())
    n_langs = len(langs)

    status = st.empty()
    progress = st.progress(0)

    # Pages reviewed from screenshots
    pages = ", ".join(s["name"] for s in st.session_state.screenshots) if st.session_state.screenshots else ""

    try:
        for lang_i, lang in enumerate(langs):
            cur = st.session_state.audits[lang]

            benchmark_text = ""
            if st.session_state.benchmark != "none":
                benchmark_text = extract_benchmark_section(cur["text"])

            # Condense findings/benchmark into shorter, slide-ready copy.
            # The full written audit (cur) is left untouched — only the deck's
            # copy is shortened. Falls back to originals on any failure.
            condensed_findings, condensed_benchmark = condense_for_deck(
                api_key=st.session_state.api_key,
                findings=cur["findings"],
                benchmark_md=benchmark_text,
                language=lang,
            )

            def on_progress(current, total, label, _lang=lang, _lang_i=lang_i):
                pct = (_lang_i + min(current / max(total, 1), 1.0)) / n_langs
                progress.progress(pct)
                status.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#71717a;">'
                    f'<span class="spinner-dot"></span>'
                    f"({_lang}) Laying out slide {current} of {total} — {label}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            deck_bytes = generate_deck(
                findings=condensed_findings,
                product_name=st.session_state.product_name,
                language=lang,
                mode=st.session_state.mode,
                benchmark=st.session_state.benchmark,
                screenshots=st.session_state.screenshots,
                tally=cur["tally"],
                target_users=st.session_state.target_users,
                pages_reviewed=pages,
                benchmark_text=condensed_benchmark,
                competitors=st.session_state.competitors,
                comp_screenshots=st.session_state.comp_screenshots,
                progress_callback=on_progress,
            )
            st.session_state.decks[lang] = deck_bytes

        progress.progress(1.0)
        status.markdown("**Deck generated.**")
        time.sleep(0.5)
        go("deck_ready")
        st.rerun()
    except Exception as e:
        st.error(f"Deck generation failed: {str(e)}")
        if st.button("← Back to audit"):
            go("audit")
            st.rerun()


# =========================================================================
# STEP 6b — Deck ready
# =========================================================================
elif st.session_state.step == "deck_ready":
    st.markdown('<div class="screen-kicker">Step 6 of 6 — Deck</div>', unsafe_allow_html=True)
    st.markdown("## Deck ready")
    st.markdown(
        "A presentation summary of the audit, formatted for client presentation — "
        "same findings, same severity coding, shortened to fit the slide format."
    )

    langs = list(st.session_state.decks.keys())
    base_name = st.session_state.product_name.lower().replace(" ", "_")

    # Deck preview thumbnails (based on the active/first available language)
    preview_lang = st.session_state.active_language if st.session_state.active_language in st.session_state.audits else (langs[0] if langs else "")
    preview_findings = st.session_state.audits.get(preview_lang, {}).get("findings", [])

    slide_labels = ["Title", "Summary"]
    for f in preview_findings[:4]:
        slide_labels.append(f["title"][:20])
    slide_labels.append("Closing")

    preview_cols = st.columns(min(4, len(slide_labels)))
    for i, label in enumerate(slide_labels[:4]):
        with preview_cols[i % 4]:
            st.markdown(
                f'<div class="deck-thumb">{label}</div>',
                unsafe_allow_html=True,
            )

    # Download buttons — one per language, plus a zip-all when there's more than one
    st.markdown("---")
    if len(langs) > 1:
        st.caption(f"Decks generated in {len(langs)} languages — download each individually or grab them all as a .zip.")

    n_buttons = len(langs) + (1 if len(langs) > 1 else 0) + 1  # + "Start new audit"
    dl_cols = st.columns(n_buttons)

    for i, lang in enumerate(langs):
        with dl_cols[i]:
            suffix = f"_{lang.lower()}" if len(langs) > 1 else ""
            st.download_button(
                f"Download .pptx ({lang})" if len(langs) > 1 else "Download .pptx",
                data=st.session_state.decks[lang],
                file_name=f"ux_audit_{base_name}{suffix}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary",
                key=f"dl_deck_{lang}",
            )

    next_col = len(langs)
    if len(langs) > 1:
        with dl_cols[next_col]:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for lang in langs:
                    zf.writestr(f"ux_audit_{base_name}_{lang.lower()}.pptx", st.session_state.decks[lang])
            st.download_button(
                "Download all (.zip)",
                data=zip_buf.getvalue(),
                file_name=f"ux_audit_{base_name}_decks.zip",
                mime="application/zip",
                key="dl_deck_zip",
            )
        next_col += 1

    with dl_cols[next_col]:
        if st.button("Start new audit"):
            for k, v in DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()

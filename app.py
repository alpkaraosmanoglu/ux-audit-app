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
from datetime import datetime

import streamlit as st

from styles import CUSTOM_CSS
from audit_engine import (
    build_system_prompt,
    build_user_message,
    parse_findings,
    severity_tally,
    stream_audit,
    tally_string,
)
from deck_engine import generate_deck

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
    "competitors": [{"name": "", "url": ""}],
    "screenshots": [],       # list of {"name": str, "data": bytes, "mime_type": str}
    "comp_screenshots": {},   # comp_idx -> list of {"name", "data", "mime_type"}
    "audit_text": "",
    "audit_findings": [],
    "audit_tally": {},
    "deck_bytes": None,
    "generating": False,
    "deck_generating": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


def go(step: str):
    st.session_state.step = step


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

    # Competitor fields
    if st.session_state.benchmark in ("competitors", "both"):
        st.markdown("---")
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

    # Build prompt for the first selected language
    language = st.session_state.language[0] if st.session_state.language else "English"
    mode = st.session_state.mode
    benchmark = st.session_state.benchmark

    competitor_names = [c["name"] for c in st.session_state.competitors if c.get("name")]

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
    )

    urls = [u.strip() for u in st.session_state.urls_text.split("\n") if u.strip()] if st.session_state.urls_text else None

    user_message = build_user_message(
        mode=mode,
        screenshots=st.session_state.screenshots if mode in ("screenshots", "hybrid") else None,
        urls=urls if mode in ("urls", "hybrid") else None,
    )

    # Status line
    n_shots = len(st.session_state.screenshots)
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    findings_container = st.container()

    # Stream the audit
    full_text = ""
    error_msg = None

    with findings_container:
        text_area = st.empty()
        for event_type, data in stream_audit(
            api_key=st.session_state.api_key,
            system_prompt=system_prompt,
            user_message=user_message,
        ):
            if event_type == "text":
                full_text += data
                # Update progress based on content
                finding_count = full_text.count("###")
                progress_val = min(0.95, finding_count * 0.15 + 0.1)
                progress_bar.progress(progress_val)
                status_placeholder.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#71717a;">'
                    f'<span class="spinner-dot"></span>'
                    f"Analyzing… {finding_count} finding(s) so far"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                text_area.markdown(full_text)
            elif event_type == "done":
                full_text = data
                progress_bar.progress(1.0)
                status_placeholder.markdown("**Generation complete.**")
            elif event_type == "error":
                error_msg = data

    if error_msg:
        st.error(error_msg)
        if st.button("← Back to configuration"):
            go("config")
            st.rerun()
    else:
        # Parse findings
        st.session_state.audit_text = full_text
        st.session_state.audit_findings = parse_findings(full_text)
        st.session_state.audit_tally = severity_tally(st.session_state.audit_findings)

        time.sleep(0.5)
        go("audit")
        st.rerun()


# =========================================================================
# STEP 5 — Audit (review findings)
# =========================================================================
elif st.session_state.step == "audit":
    st.markdown('<div class="screen-kicker">Step 5 of 6 — Deliverable</div>', unsafe_allow_html=True)

    language = st.session_state.language[0] if st.session_state.language else "English"
    mode_labels = {"screenshots": "Screenshots", "urls": "URLs only", "hybrid": "Hybrid"}
    bench_labels = {"none": "No benchmarking", "market": "Market", "competitors": "Competitors", "both": "Market + Competitors"}

    st.markdown(f"## UX Audit — {st.session_state.product_name}")
    st.caption(
        f"{mode_labels.get(st.session_state.mode, st.session_state.mode)} mode · "
        f"{language} · "
        f"{bench_labels.get(st.session_state.benchmark, 'None')} · "
        f"Generated {datetime.now().strftime('%b %d, %Y')}"
    )

    findings = st.session_state.audit_findings
    tally = st.session_state.audit_tally

    # Build a screenshot lookup dict for display
    shot_lookup = {}
    for shot in st.session_state.screenshots:
        shot_lookup[shot["name"]] = shot["data"]

    if findings:
        for f in findings:
            sev_class = f"sev-{f['severity']}"

            # Try to find matching screenshot
            shot_name = None
            ev = f.get("evidence", "")
            if ev:
                import re as re_mod
                match = re_mod.search(r"(\S+\.(?:png|jpg|jpeg|webp))", ev)
                if match:
                    shot_name = match.group(1)

            shot_data = None
            if shot_name:
                shot_data = shot_lookup.get(shot_name)
                if not shot_data:
                    # Fuzzy match
                    for k, v in shot_lookup.items():
                        if shot_name.lower() in k.lower() or k.lower() in shot_name.lower():
                            shot_data = v
                            break

            col_img, col_text = st.columns([1, 4])
            with col_img:
                if shot_data:
                    st.image(shot_data, use_container_width=True)
                else:
                    st.markdown(
                        f'<div class="finding-shot">{ev or "—"}</div>',
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
        st.markdown(st.session_state.audit_text)

    # --- Action bar ---
    st.markdown("---")
    tally_str = tally_string(tally, language) if tally else ""
    st.caption(tally_str)

    action_cols = st.columns([1, 1, 1, 1])
    with action_cols[0]:
        if st.button("Regenerate", type="secondary"):
            go("generating")
            st.rerun()
    with action_cols[1]:
        st.download_button(
            "Download .md",
            data=st.session_state.audit_text,
            file_name=f"ux_audit_{st.session_state.product_name.lower().replace(' ', '_')}.md",
            mime="text/markdown",
        )
    with action_cols[2]:
        if st.button("Generate deck →", type="primary"):
            go("deck_generating")
            st.rerun()
    with action_cols[3]:
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

    language = st.session_state.language[0] if st.session_state.language else "English"

    status = st.empty()
    progress = st.progress(0)

    def on_progress(current, total, label):
        pct = min(current / max(total, 1), 1.0)
        progress.progress(pct)
        status.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;font-size:13px;color:#71717a;">'
            f'<span class="spinner-dot"></span>'
            f"Laying out slide {current} of {total} — {label}"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Build screenshot lookup for deck
    shot_dict = {}
    for shot in st.session_state.screenshots:
        shot_dict[shot["name"]] = shot["data"]

    # Extract benchmark text from audit
    benchmark_text = ""
    if st.session_state.benchmark != "none":
        bench_match = re.search(
            r"##\s+(?:Market|Competitor|Benchmark|Kıyaslama|Marktvergleich|Wettbewerbsvergleich).+",
            st.session_state.audit_text,
            re.DOTALL,
        )
        if bench_match:
            benchmark_text = bench_match.group(0)

    # Pages reviewed from screenshots
    pages = ", ".join(s["name"] for s in st.session_state.screenshots) if st.session_state.screenshots else ""

    try:
        deck_bytes = generate_deck(
            findings=st.session_state.audit_findings,
            product_name=st.session_state.product_name,
            language=language,
            mode=st.session_state.mode,
            benchmark=st.session_state.benchmark,
            screenshots=shot_dict,
            tally=st.session_state.audit_tally,
            target_users=st.session_state.target_users,
            pages_reviewed=pages,
            benchmark_text=benchmark_text,
            progress_callback=on_progress,
        )
        st.session_state.deck_bytes = deck_bytes
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
        "same findings, same severity coding."
    )

    # Deck preview thumbnails
    n_findings = len(st.session_state.audit_findings)
    slide_labels = ["Title", "Summary"]
    for f in st.session_state.audit_findings[:4]:
        slide_labels.append(f["title"][:20])
    slide_labels.append("Closing")

    preview_cols = st.columns(min(4, len(slide_labels)))
    for i, label in enumerate(slide_labels[:4]):
        with preview_cols[i % 4]:
            st.markdown(
                f'<div class="deck-thumb">{label}</div>',
                unsafe_allow_html=True,
            )

    # Download buttons
    st.markdown("---")
    dl_cols = st.columns([1, 1, 1])
    with dl_cols[0]:
        if st.session_state.deck_bytes:
            st.download_button(
                "Download .pptx",
                data=st.session_state.deck_bytes,
                file_name=f"ux_audit_{st.session_state.product_name.lower().replace(' ', '_')}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                type="primary",
            )
    with dl_cols[1]:
        st.caption("PDF export requires LibreOffice — not available on Streamlit Cloud. Download the .pptx and export locally.")
    with dl_cols[2]:
        if st.button("Start new audit"):
            for k, v in DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()

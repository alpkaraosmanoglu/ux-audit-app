"""UX Audit Studio — Streamlit app.

BYOK (bring-your-own-key): each user pastes their Anthropic API key.
Nothing is stored server-side beyond the session.
"""

import os
import io
import base64
import zipfile
import subprocess
from pathlib import Path

import streamlit as st
from anthropic import Anthropic
from PIL import Image

# ============================================================
# CONFIG
# ============================================================

APP_DIR = Path(__file__).parent
SKILLS_DIR = APP_DIR / "skills"
AUDIT_SKILL_DIR = SKILLS_DIR / "ux-audit-skill"
DECK_SKILL_DIR = SKILLS_DIR / "ux-audit-deck-skill"

# Kararlı ve güncel Anthropic model ismi tanımlandı
MODEL = "claude-3-5-sonnet-latest" 

# ============================================================
# HELPERS
# ============================================================


def load_skill_prompt(skill_dir: Path) -> str:
    """Load a skill's SKILL.md plus all its reference files, concatenated.

    Simpler than progressive disclosure but reliable for a single-shot API call.
    """
    parts = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        parts.append(f"# SKILL: {skill_dir.name}\n\n{skill_md.read_text()}")

    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        for ref_file in sorted(refs_dir.glob("*.md")):
            parts.append(
                f"\n\n---\n# REFERENCE: {ref_file.name}\n\n{ref_file.read_text()}"
            )

    return "\n".join(parts)


def image_to_base64(image_bytes: bytes) -> str:
    return base64.standard_b64encode(image_bytes).decode("utf-8")


def build_message_content(user_text: str, screenshots: list) -> list:
    """Build a multi-part message with text + images for the Claude API."""
    content = []
    for i, ss in enumerate(screenshots, 1):
        image_data = ss.getvalue()
        media_type = "image/png" if ss.name.lower().endswith(".png") else "image/jpeg"
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_to_base64(image_data),
                },
            }
        )
        content.append({"type": "text", "text": f"Screenshot {i}: {ss.name}"})
    content.append({"type": "text", "text": user_text})
    return content


def run_claude(client: Anthropic, system_prompt: str, user_message: list) -> str:
    """Run a Claude API call with streaming, return the full text."""
    response_placeholder = st.empty()
    accumulated = ""

    with client.messages.stream(
        model=MODEL,
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            accumulated += text
            response_placeholder.markdown(accumulated + "▌")

    response_placeholder.markdown(accumulated)
    return accumulated


# ============================================================
# UI
# ============================================================

st.set_page_config(page_title="UX Audit Studio", page_icon="🔍", layout="wide")

st.title("UX Audit Studio")
st.caption(
    "Structured UX audits from screenshots. Grounded in classic UX frameworks. "
    "Produces a written audit and a presentation deck."
)

# --- Sidebar: API key ---
with st.sidebar:
    st.header("Setup")
    api_key = st.text_input(
        "Anthropic API key",
        type="password",
        value=st.session_state.get("api_key", ""),
        help=(
            "Bring your own key from console.anthropic.com. "
            "The key stays in your browser session only — never stored or logged."
        ),
    )
    if api_key:
        st.session_state.api_key = api_key.strip()
        st.success("Key set for this session.")
    else:
        if "api_key" in st.session_state:
            del st.session_state["api_key"]

    st.divider()
    st.caption("**Source:** the audit method is defined by files in the `skills/` folder.")
    st.caption(
        "**Costs:** each audit calls Claude with your key. "
        "A typical audit costs $0.20–$0.80 depending on screenshot count."
    )

# --- Main form ---

# GÜVENLİ KONTROL: Session state içinde api_key anahtarı var mı ve içi gerçekten dolu mu?
if "api_key" not in st.session_state or not st.session_state.api_key:
    st.warning("👈 Paste your Anthropic API key in the sidebar to start.")
    st.stop()

# İstemciyi sadece geçerli bir API anahtarı olduğunda güvenli başlatma
try:
    client = Anthropic(api_key=st.session_state.api_key)
except Exception as e:
    st.error(f"Anthropic istemcisi başlatılamadı. Hata: {e}")
    st.stop()

# Initialize session state
for key, default in [
    ("audit_text", None),
    ("audit_config", None),
    ("screenshots", []),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- Form for configuring the audit ---
with st.form("audit_config_form"):
    st.subheader("1. Language")
    language = st.radio(
        "Which language?",
        ["English", "Türkçe", "Deutsch"],
        horizontal=True,
    )

    st.subheader("2. Mode")
    mode = st.radio(
        "How will you provide the product?",
        [
            "Screenshots (recommended)",
            "URLs only",
            "Hybrid (URLs + screenshots)",
        ],
    )
    st.caption(
        "Screenshots gives you a full visual audit. URLs only produces a "
        "structural audit — no visual analysis. See the sidebar for details."
    )

    st.subheader("3. Benchmarking")
    benchmark = st.radio(
        "Include benchmarks?",
        ["None", "Market only", "Competitors only", "Both"],
    )

    competitors = ""
    market = ""
    if benchmark in ["Competitors only", "Both"]:
        competitors = st.text_area(
            "Competitors (one per line, or leave blank to have Claude suggest based on product/market)",
            placeholder="Cuvva\nLemonade\nAllianz Direct",
        )
    if benchmark in ["Market only", "Both"]:
        market = st.text_input(
            "Market / sector",
            placeholder="e.g. B2B pharmacy platforms, direct-to-consumer insurance, rural e-commerce",
        )

    st.subheader("4. Context")
    product_name = st.text_input("Product name and category *", placeholder="e.g. LANDI — Swiss rural retail e-commerce")
    target_users = st.text_area(
        "Target users (optional)",
        placeholder="Leave blank if unknown — Claude will infer from context.",
        height=80,
    )
    audience = st.text_input(
        "Audience for the audit (optional)",
        placeholder="e.g. senior leadership, internal product team",
    )
    scope = st.text_area(
        "Scope (optional)",
        placeholder="Which flows or pages to focus on",
        height=80,
    )

    st.subheader("5. Screenshots")
    screenshots = st.file_uploader(
        "Upload product screenshots",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="Label them clearly if you can — Claude will reference them by number.",
    )

    competitor_screenshots = None
    if benchmark in ["Competitors only", "Both"]:
        competitor_screenshots = st.file_uploader(
            "Competitor screenshots (optional, strongly recommended for benchmark slides)",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
        )

    urls = ""
    if mode in ["URLs only", "Hybrid (URLs + screenshots)"]:
        urls = st.text_area(
            "URLs (one per line)",
            placeholder="https://example.com/homepage\nhttps://example.com/product",
        )

    generate = st.form_submit_button("Generate audit →", type="primary")

# --- Run audit ---

if generate:
    if not product_name:
        st.error("Product name is required.")
        st.stop()
    if mode == "Screenshots (recommended)" and not screenshots:
        st.error("Please upload at least one screenshot.")
        st.stop()

    st.session_state.audit_config = {
        "language": language,
        "mode": mode,
        "benchmark": benchmark,
        "competitors": competitors,
        "market": market,
        "product_name": product_name,
        "target_users": target_users,
        "audience": audience,
        "scope": scope,
        "urls": urls,
    }
    st.session_state.screenshots = screenshots or []
    st.session_state.competitor_screenshots = competitor_screenshots or []

    # Build the user message from the form
    context_lines = [
        f"**Language chosen:** {language}",
        f"**Mode chosen:** {mode}",
        f"**Benchmarking scope:** {benchmark}",
    ]
    if competitors:
        context_lines.append(f"**Competitors:** {competitors}")
    if market:
        context_lines.append(f"**Market/sector:** {market}")
    context_lines.append(f"**Product:** {product_name}")
    if target_users:
        context_lines.append(f"**Target users:** {target_users}")
    else:
        context_lines.append("**Target users:** Not specified — infer from product context.")
    if audience:
        context_lines.append(f"**Audience for audit:** {audience}")
    if scope:
        context_lines.append(f"**Scope:** {scope}")
    if urls:
        context_lines.append(f"**URLs:** {urls}")

    user_text = (
        "The user has already answered your language, mode, and benchmark questions. "
        "Skip Step 0a, 0b, 0c and proceed directly to Phase 1 — the written audit — "
        "in the chosen language.\n\n"
        + "\n".join(context_lines)
        + f"\n\n**Screenshots attached:** {len(screenshots or [])}"
    )

    system_prompt = load_skill_prompt(AUDIT_SKILL_DIR)
    message_content = build_message_content(user_text, screenshots or [])

    st.subheader("Written audit")
    with st.spinner("Running audit..."):
        try:
            audit_text = run_claude(client, system_prompt, message_content)
            st.session_state.audit_text = audit_text
            st.success("Audit complete. Scroll down to generate the presentation deck.")
        except Exception as ex:
            st.error(f"API Call failed. Error detail: {ex}")

# --- Deck generation ---

if st.session_state.audit_text:
    st.divider()
    st.subheader("Presentation deck")
    st.caption("Generate the .pptx and .pdf using the adesso template.")

    if st.button("Generate deck →", type="primary"):
        deck_system = load_skill_prompt(DECK_SKILL_DIR)

        deck_user = (
            "Generate the presentation deck for this audit. Use the adesso template "
            "bundled with the skill (assets/adesso_template.pptx). Below is the completed "
            "written audit — parse it and produce the .pptx following the skill's slide "
            "sequence.\n\n"
            "**Written audit:**\n\n"
            + st.session_state.audit_text
            + "\n\n**Language:** "
            + st.session_state.audit_config["language"]
            + "\n\n**Screenshots available:** filenames as attached in this message.\n\n"
            "Write a Python script that builds the deck using python-pptx."
        )

        st.info(
            "Note: For this MVP, the deck skill is provided as reference. "
            "In v2, the app will execute the Python script server-side."
        )

    # --- Download the written audit ---
    st.download_button(
        "Download written audit (.md)",
        data=st.session_state.audit_text,
        file_name="ux_audit.md",
        mime="text/markdown",
    )
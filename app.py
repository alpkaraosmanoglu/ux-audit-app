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

# Kararlı ve güncel bir model ismi atandı
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

# API Key kontrolü
if "api_key" not in st.session_state or not st.session_state.api_key:
    st.warning("👈 Paste your Anthropic API key in the sidebar to start.")
    st.stop()

# İstemciyi güvenli başlatma
try:
    client = Anthropic(api_key=st.session_state.api_key)
except Exception as e:
    st.error(f"Anthropic istemcisi başlatılamadı. Hata: {e}")
    st.stop()

# Initialize session state
for key, default in
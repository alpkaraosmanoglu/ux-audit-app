"""Custom CSS for UX Audit Studio — approximates the modernist design system."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

:root {
    --accent: #6f5cf6;
    --accent-dim: rgba(111, 92, 246, 0.08);
    --bg: #fafafa;
    --fg: #0b0b0c;
    --muted: #71717a;
    --border: #e4e4e7;
    --card-bg: #ffffff;
    --sev-major: #a3271d;
    --sev-major-bg: #fef2f2;
    --sev-mid: #a3671d;
    --sev-mid-bg: #fffbeb;
    --sev-minor: #8a7a12;
    --sev-minor-bg: #fefce8;
    --sev-open: #2f5fa3;
    --sev-open-bg: #eff6ff;
    --success: #16a34a;
}

/* Global overrides */
.stApp {
    font-family: 'DM Sans', sans-serif !important;
}
section[data-testid="stSidebar"] { display: none !important; }

/* Top nav */
.topnav-bar {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 12px 24px;
    border-bottom: 2px solid var(--border);
    background: var(--card-bg);
    position: sticky;
    top: 0;
    z-index: 999;
    font-family: 'DM Sans', sans-serif;
}
.topnav-bar .brand {
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--fg);
    margin-right: 8px;
}
.topnav-bar .navlink {
    font-size: 11px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--muted);
    text-decoration: none;
    cursor: default;
}
.topnav-bar .navlink.active {
    color: var(--accent);
}

/* Hero */
.hero-title {
    font-size: 40px;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: -0.01em;
    line-height: 1.1;
    max-width: 680px;
    margin-bottom: 12px;
    color: var(--fg);
    font-family: 'DM Sans', sans-serif;
}
.hero-sub {
    font-size: 15px;
    max-width: 460px;
    color: var(--muted);
    line-height: 1.5;
}
.byok-notice {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--muted);
    margin-top: 16px;
}

/* Screen kicker */
.screen-kicker {
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 6px;
    font-weight: 500;
}

/* Mode cards */
.mode-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0;
    border: 2px solid var(--border);
}
.mode-card {
    padding: 16px;
    border-right: 2px solid var(--border);
    cursor: pointer;
    transition: background 0.15s;
}
.mode-card:last-child { border-right: none; }
.mode-card.selected {
    background: var(--accent-dim);
}
.mode-card h4 {
    margin: 0 0 8px 0;
    font-size: 15px;
    font-weight: 600;
}
.mode-badge {
    font-size: 10px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--accent);
    border: 1.5px solid var(--accent);
    padding: 2px 8px;
    display: inline-block;
    margin-bottom: 8px;
    font-weight: 600;
}
.pro-item { color: var(--success); font-size: 12px; }
.con-item { color: var(--muted); font-size: 12px; }

/* Severity tags */
.sev-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 3px 10px;
    margin-bottom: 8px;
    border: 1.5px solid currentColor;
    font-family: 'DM Mono', monospace;
}
.sev-major { color: var(--sev-major); background: var(--sev-major-bg); }
.sev-mid { color: var(--sev-mid); background: var(--sev-mid-bg); }
.sev-minor { color: var(--sev-minor); background: var(--sev-minor-bg); }
.sev-open { color: var(--sev-open); background: var(--sev-open-bg); }

/* Finding card */
.finding-card {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 24px;
    padding: 24px 0;
    border-bottom: 2px solid var(--border);
    font-family: 'DM Sans', sans-serif;
}
.finding-card:last-child { border-bottom: none; }
.finding-shot {
    border: 2px solid var(--border);
    aspect-ratio: 4/3;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
    font-family: 'DM Mono', monospace;
    color: var(--muted);
    text-align: center;
    background: repeating-linear-gradient(135deg, #f4f4f5 0 8px, #fafafa 8px 16px);
    overflow: hidden;
}
.finding-shot img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.finding-title {
    font-weight: 400;
    font-size: 16px;
    line-height: 1.3;
    margin: 4px 0;
    color: var(--fg);
}
.finding-body {
    font-size: 13px;
    line-height: 1.55;
    color: #3f3f46;
    margin-top: 6px;
}
.finding-cite {
    margin-top: 10px;
    border-left: 2px solid var(--fg);
    padding: 8px 12px;
    font-size: 12px;
    color: var(--muted);
    background: #f4f4f5;
}

/* Thumbnail grid */
.thumb-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-top: 12px;
}
.thumb {
    border: 2px solid var(--border);
    aspect-ratio: 4/3;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    background: repeating-linear-gradient(135deg, #f4f4f5 0 8px, #fafafa 8px 16px);
}
.thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.thumb-label {
    position: absolute;
    left: 0; right: 0; bottom: 0;
    background: rgba(255,255,255,0.88);
    font-size: 9px;
    font-family: 'DM Mono', monospace;
    color: var(--muted);
    text-align: center;
    padding: 2px 4px;
}

/* Progress */
.progress-wrap {
    margin-top: 12px;
}
.progress-bar {
    height: 2px;
    background: var(--border);
    position: relative;
    margin-top: 8px;
}
.progress-fill {
    height: 100%;
    background: var(--accent);
    transition: width 0.4s linear;
}

/* Deck grid */
.deck-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-top: 12px;
}
.deck-thumb {
    border: 2px solid var(--border);
    aspect-ratio: 16/9;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
    font-family: 'DM Mono', monospace;
    color: var(--muted);
    background: repeating-linear-gradient(135deg, #f4f4f5 0 8px, #fafafa 8px 16px);
}

/* Sticky bottom bar */
.sticky-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 999;
    background: var(--card-bg);
    border-top: 2px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
}
.sticky-bar .meta {
    font-size: 12px;
    color: var(--muted);
}

/* Key field */
.key-field-wrap {
    position: relative;
    max-width: 420px;
}
.key-valid-check {
    color: var(--success);
    font-weight: 600;
}
.key-error {
    border: 1.5px solid var(--sev-major);
    color: var(--sev-major);
    font-size: 12px;
    padding: 8px 10px;
    margin-top: 8px;
}

/* Benchmarking description */
.bench-desc {
    font-size: 12px;
    color: var(--muted);
    margin-top: 6px;
}

/* Streamlit button overrides */
div.stButton > button[kind="primary"],
div.stButton > button[data-testid="stBaseButton-primary"] {
    background-color: var(--accent) !important;
    border-color: var(--accent) !important;
    color: white !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    border-radius: 0 !important;
}
div.stButton > button[kind="primary"]:hover,
div.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background-color: #5b47e0 !important;
    border-color: #5b47e0 !important;
}
div.stButton > button[kind="secondary"],
div.stButton > button[data-testid="stBaseButton-secondary"] {
    border-radius: 0 !important;
    font-family: 'DM Sans', sans-serif !important;
}

/* Section label */
.section-label {
    font-size: 12px;
    font-weight: 500;
    color: var(--fg);
    margin-bottom: 8px;
    display: block;
}

/* Summary tally */
.tally-line {
    font-size: 12px;
    color: var(--muted);
}

/* Spinner animation */
@keyframes spin { to { transform: rotate(360deg); } }
.spinner-dot {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    display: inline-block;
    vertical-align: middle;
    margin-right: 8px;
}

/* Cursor blink for streaming */
@keyframes blink { 0%,50%{opacity:1} 51%,100%{opacity:0} }
.cursor-blink {
    display: inline-block;
    width: 2px;
    height: 16px;
    background: var(--accent);
    vertical-align: -3px;
    animation: blink 1s step-end infinite;
    margin-left: 2px;
}

/* Hide Streamlit branding */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; }

/* Padding adjustments */
.block-container {
    padding-top: 0 !important;
    max-width: 1120px !important;
}
</style>
"""

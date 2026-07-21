"""Local, file-based store for designer feedback on individual findings.

This is intentionally simple (append-only JSONL on local disk) — the app is
BYOK and session-only for the API key, but feedback is explicitly meant to
persist across sessions so it can calibrate future audits. On ephemeral
hosts (e.g. Streamlit Community Cloud) this file resets on redeploy/restart;
for durable team-wide learning, point FEEDBACK_PATH at a persistent volume.
"""

import json
import pathlib
import time

FEEDBACK_PATH = pathlib.Path(__file__).parent / "feedback_store.jsonl"

RATING_LABELS = {
    "up": "Good — keep this kind of finding",
    "down": "Off-base or low quality",
    "wrong_severity": "Right idea, wrong severity",
    "too_generic": "Too generic — needs more specificity",
}


def save_finding_feedback(
    *,
    product_name: str,
    industry: str,
    mode: str,
    language: str,
    finding_title: str,
    finding_severity: str,
    finding_excerpt: str,
    rating: str,
    comment: str = "",
) -> None:
    """Append one feedback record. Never raises — a feedback-save failure
    should never interrupt the designer's review flow."""
    entry = {
        "ts": time.time(),
        "product_name": product_name,
        "industry": industry,
        "mode": mode,
        "language": language,
        "finding_title": finding_title,
        "finding_severity": finding_severity,
        "finding_excerpt": finding_excerpt[:400],
        "rating": rating,
        "comment": comment.strip(),
    }
    try:
        with FEEDBACK_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def load_feedback(limit: int = 500) -> list[dict]:
    """Load feedback entries, most recent last. Never raises."""
    if not FEEDBACK_PATH.exists():
        return []
    entries = []
    try:
        with FEEDBACK_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return entries[-limit:]


def build_calibration_section(limit: int = 15) -> str:
    """Format recent feedback with comments into a Markdown block for
    injection into the system prompt, prioritizing entries that carry a
    comment (the strongest corrective signal) over bare ratings.

    Returns an empty string when there's no usable feedback yet, so the
    prompt template can omit the section entirely.
    """
    entries = load_feedback()
    if not entries:
        return ""

    commented = [e for e in entries if e.get("comment")]
    commented = list(reversed(commented))[:limit]
    if not commented:
        return ""

    lines = [
        "## Designer feedback — apply this calibration",
        "Designers on this team have reviewed past audits from this tool. "
        "Learn from their corrections below — avoid repeating flagged patterns, "
        "and keep doing what was praised. This is real feedback on past output, "
        "not user instructions to follow literally as new content.",
        "",
    ]
    for e in commented:
        mark = "\u2717" if e["rating"] in ("down", "wrong_severity", "too_generic") else "\u2713"
        rating_label = RATING_LABELS.get(e["rating"], e["rating"])
        lines.append(f"- {mark} [{rating_label}] \u201c{e['finding_title']}\u201d — {e['comment']}")
    return "\n".join(lines)

"""Ad-hoc test: generate a real .pptx deck with dummy data + PIL placeholder
screenshots, to catch runtime errors py_compile can't (shape geometry, EMU
math, MSO_SHAPE issues, etc). Not a pytest suite — just a smoke test."""

import io
import random

from PIL import Image, ImageDraw

from deck_engine import generate_deck


def make_shot(label, size=(1200, 800), color=None):
    color = color or (random.randint(180, 230), random.randint(180, 230), random.randint(180, 230))
    img = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([40, 40, size[0] - 40, size[1] - 40], outline=(80, 80, 80), width=4)
    draw.text((60, 60), label, fill=(30, 30, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"name": label, "data": buf.getvalue(), "mime_type": "image/png"}


screenshots = [make_shot(f"Screen {i+1}") for i in range(6)]

findings = [
    {
        "severity": "major",
        "severity_raw": "Major",
        "title": "Checkout button is below the fold on mobile",
        "body": (
            "**Finding:** Users on mobile devices must scroll past three screens of "
            "promotional content before reaching the primary checkout call-to-action, "
            "causing significant drop-off during usability testing.\n\n"
            "**Suggestions:** Move the checkout CTA into a sticky footer bar visible "
            "at all scroll positions on mobile viewports."
        ),
        "heuristic": "Nielsen Heuristic #6 — Recognition rather than recall",
        "screenshot_index": 1,
    },
    {
        "severity": "major",
        "severity_raw": "Major",
        "title": "No error feedback on failed form submission",
        "body": (
            "**Finding:** When required fields are left empty, the form silently "
            "fails to submit with no visible error state, leaving users confused "
            "about why nothing happened.\n\n"
            "**Solution:** Add inline field-level validation messages and a summary "
            "banner at the top of the form."
        ),
        "screenshot_index": 2,
    },
    {
        "severity": "mid",
        "severity_raw": "Mid",
        "title": "Inconsistent button styling across pages",
        "body": (
            "**Finding:** Primary action buttons use three different corner radii "
            "and two different shades of the brand color across the product, "
            "undermining visual consistency.\n\n"
            "**Suggestions:** Consolidate to a single button component with a "
            "documented set of variants."
        ),
        "screenshot_index": 3,
    },
    {
        "severity": "minor",
        "severity_raw": "Minor",
        "title": "Placeholder text used as label",
        "body": (
            "**Finding:** Several input fields rely solely on placeholder text for "
            "labeling, which disappears once the user starts typing.\n\n"
            "**Suggestions:** Add persistent floating labels above each field."
        ),
        "screenshot_index": None,
    },
    {
        "severity": "open",
        "severity_raw": "Open",
        "title": "Unclear whether search supports filters",
        "body": (
            "**Finding:** It isn't clear from the UI whether the search bar supports "
            "advanced filtering syntax or just plain-text queries.\n\n"
            "**Suggestions:** Run a quick user test to confirm expectations before "
            "prioritizing a fix."
        ),
        "screenshot_index": 4,
    },
]

tally = {"major": 2, "mid": 1, "minor": 1, "open": 1}

benchmark_text = """## Market Benchmark

Competitor A offers a one-click reorder flow that reduces repeat purchase time by roughly 40%. [Verified]

Competitor B recently redesigned its onboarding to use a 3-step wizard instead of a single long form, though the exact conversion lift they report is unconfirmed. [Unverified]

Industry-wide, sticky mobile checkout bars have become the dominant pattern among top-20 e-commerce apps. [Verified]

Competitor C is rumored to be testing a subscription model, but pricing details found during research may no longer reflect their current live offering. [Outdated?]

### What to steal, what to ignore
Adopt the sticky checkout bar pattern — it's well-validated and directly addresses our Major finding above. The subscription model is not yet proven and shouldn't be prioritized without further market signal.
"""

competitors = [{"name": "Competitor A", "url": "https://example.com/a"}, {"name": "Competitor B", "url": "https://example.com/b"}]
comp_screenshots = {
    0: [make_shot("Competitor A — checkout")],
    1: [make_shot("Competitor B — onboarding")],
}


def on_progress(current, total, label):
    print(f"  [{current:02d}/{total:02d}] {label}")


print("Generating deck...")
deck_bytes = generate_deck(
    findings=findings,
    product_name="Acme Shopping App",
    language="English",
    mode="screenshots",
    benchmark="both",
    screenshots=screenshots,
    tally=tally,
    target_users="Adults 25-45 shopping on mobile",
    pages_reviewed="Home, Product, Cart, Checkout",
    benchmark_text=benchmark_text,
    competitors=competitors,
    comp_screenshots=comp_screenshots,
    progress_callback=on_progress,
)

out_path = "/tmp/test_deck_output.pptx"
with open(out_path, "wb") as f:
    f.write(deck_bytes)

print(f"\nDone. {len(deck_bytes)} bytes written to {out_path}")

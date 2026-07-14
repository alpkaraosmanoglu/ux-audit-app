---
name: ux-audit-deck
description: Generate a PowerPoint presentation (.pptx) and PDF from a completed UX audit, using the adesso template. Renders each finding as a slide with the finding text on the left and the screenshot on the right, adds section dividers by severity, optionally includes benchmark slides with competitor screenshots, and produces both editable .pptx and shareable .pdf. Use this skill whenever the user has a completed UX audit and wants a presentation deck — typically loaded as the handoff step from the ux-audit skill, but can also run standalone if the user brings a pre-written audit.
---

# UX Audit Deck Generator

Generate a presentation deck from a completed UX audit. Uses the adesso PowerPoint template as the visual foundation. Produces both `.pptx` (editable) and `.pdf` (for sharing).

This skill is Phase 2 of the audit workflow. It expects a completed written audit as input — either handed off from the `ux-audit` skill, or provided directly by the user.

## Inputs required

- **The written audit** — findings with severity tags, titles, finding text, solutions/suggestions, evidence references. Also cover-section metadata (product name, pages reviewed, target users, severity tally, mode indicator, benchmark scope).
- **Screenshots** — the image files referenced in each finding's evidence line (e.g., "Screenshot 4 — basket overview page").
- **Competitor screenshots** (optional) — image files for each competitor in the benchmark section, if benchmarking was included and the user shared them.
- **The adesso template** (`.potx` or `.pptx`) — a copy is bundled in `assets/adesso_template.pptx` for reference, but the user typically provides their own.
- **Language** — English, Turkish, or German. Same as the written audit.

## Template handling — do this first

The adesso template ships as `.potx`. Two things will break python-pptx if not handled:

1. **If `.potx`:** rename to `.pptx` first. Python-pptx rejects `.potx` extensions.
2. **Content-type fix:** the template's internal manifest may still declare itself as a template, causing python-pptx to reject it with `ValueError: file is not a PowerPoint file, content type is 'application/vnd.openxmlformats-officedocument.presentationml.template.main+xml'`. Fix with:

```bash
mkdir tmp_unzip && cd tmp_unzip && unzip -q ../template.pptx
sed -i 's|presentationml.template.main+xml|presentationml.presentation.main+xml|' '[Content_Types].xml'
zip -qr ../template_fixed.pptx . && cd ..
```

The bundled `assets/adesso_template.pptx` is already fixed. Use it if the user's template can't be located or is broken.

## Layout mapping

For the exact adesso template layout indices, placeholder positions, and which layout to use for each slide type, read `references/adesso_layouts.md`.

At a glance:
- Cover: layout 2 (Titleslide BLUE)
- Overview: layout 14 (Title and Content WHITE)
- Section dividers: layout 8 (Section Header WHITE)
- Finding with screenshot: layout 20 (Content with Picture WHITE) — text left, picture right
- Finding without screenshot: layout 14 (Title and Content WHITE)
- Two-screenshot finding: layout 16 (Two Content WHITE)
- Benchmark competitor slide with screenshot: layout 20
- Benchmark competitor slide without screenshot: layout 14
- Closing: layout 28 (Claim WHITE)

## Slide sequence

1. **Cover** — title in the pattern `[Product] — UX Audit Report` (EN) / `[Ürün] — UX Denetim Raporu` (TR) / `[Produkt] — UX-Audit-Bericht` (DE). Subtitle: month/year.
2. **Overview** — pages reviewed, target users (or the not-specified note), severity tally, mode indicator, and benchmark scope if applicable. As a 4-6 line bolded-label list.
3. **Section divider for each non-empty severity level** — "Major Findings" / "Önemli Tespitler" / "Wichtige Befunde", with a body line like "2 findings at this severity".
4. **One slide per finding.** Slide title: `[severity tag] — [short finding title]` (≤36 chars total). Body: Finding text with bold "Finding:" label, then Suggestions/Solution with its bold label, then optional Heuristic / Strategic frame / Suggested research lines. Screenshot embedded on the right (layout 20) via the scale-to-fit pattern below.
5. **Benchmark section** (if benchmarking was in the audit):
   - Section divider ("Market Benchmark" / "Competitor Benchmark" / "Benchmarks" depending on scope).
   - One slide per competitor: layout 20 if a competitor screenshot was provided, layout 14 if not. Body: what the competitor does, notable patterns (with Kano tier), comparison to the audited product.
   - Market patterns: layout 14 content slide(s), typically 1-2 slides for 3-5 patterns.
   - Synthesis slide with the "What to steal, what to ignore" paragraph.
6. **Closing** — thank-you / next steps text.

## Building the deck — critical patterns

Two Python patterns are essential. Both are in `scripts/pptx_helpers.py` ready to import.

### Pattern 1 — scale-to-fit picture insertion

python-pptx's default `placeholder.insert_picture(path)` crops/zooms wide screenshots past slide bounds. This causes visible overflow past the slide edge. Use the `insert_image_fit()` helper instead — it removes the placeholder and inserts the image as a sized shape, preserving aspect ratio and centering within the original placeholder bounds.

### Pattern 2 — zip dedup after save

When you delete a slide from the template's `<p:sldIdLst>` or reorder slides via python-pptx, the original slide XML files stay in the zip archive even though they're no longer referenced. New slides added afterward can collide with the orphaned names, producing duplicate-name warnings on save and causing some renderers (including LibreOffice, which we use for the PDF conversion step) to reject the file with "source file could not be loaded."

After `prs.save()`, always run `dedup_zip()` from `scripts/pptx_helpers.py`. Use the deduped file as the final deliverable.

## Rules

- **Slide title ≤36 chars** — hard limit imposed by the template's title placeholder dimensions. Longer titles wrap to 3+ lines and overlap body text. If a finding title exceeds this, either shorten it or split the finding across two slides.
- **Body text should generally stay under ~200 words per finding** — including all optional lines (Heuristic, Strategic frame, Suggested research). If a finding genuinely needs more, split across two slides rather than overflowing.
- **Embed screenshots wherever they exist.** Never leave a picture placeholder empty. If a finding has no screenshot, use layout 14 (text-only) instead of layout 20.
- **Language consistency throughout.** Every slide title, body text, label, and section header stays in the audit's chosen language.
- **Adesso template is a reference, not a cage.** Respect its visual language as the baseline — colors, typography, layout logic — but decorative additions are fine when they genuinely enhance a specific slide (e.g., a colored callout box on a strategic-frame slide, alternating row shading on a comparison table, a highlight arrow pointing at a specific detail in a screenshot). Avoid random flourishes that don't serve the content — no unrelated emoji, no clashing color accents, no "modern" layouts that fight the template's clean structure. When in doubt, follow the template.

## PDF export

Always produce both formats. The PDF is essentially free — LibreOffice already produces one as part of the visual-QA step:

```bash
python /mnt/skills/public/pptx/scripts/office/soffice.py --headless --convert-to pdf output_clean.pptx
```

## Visual QA — required before delivery

After generating and deduping the .pptx and converting to PDF, run a visual QA pass:

```bash
pdftoppm -jpeg -r 100 output_clean.pdf slide
```

This produces one JPEG per slide. Inspect each for:
- Title overflow (title wrapping to 3+ lines and overlapping body)
- Body text overflow past the placeholder
- Missing screenshots on layout-20 slides (empty right side)
- Leftover template placeholder text ("Title of the presentation", "Second level", etc.)
- Screenshots overflowing past the slide edge

If any user-visible defect appears, fix once and re-verify. Stop after one fix-and-verify cycle unless a new defect appears.

For the detailed QA checklist including how to grid-render all slides for a fast overview, read `references/qa_checklist.md`.

## Final delivery

Present both files with a one-line summary in the audit's chosen language. Include mode, benchmark scope, and finding count. Examples:

- EN: *"Audit deck generated — Screenshots mode, Both benchmark scope with 3 competitor screenshots — 16 slides, 2 Major / 1 Mid / 1 Minor findings. Both .pptx (editable) and .pdf (for sharing) are ready."*
- TR: *"Denetim sunumu hazır — Ekran görüntüsü modu, Pazar + Rakip kıyaslamalı — 14 slayt, 3 Önemli / 2 Orta / 1 Hafif tespit. Hem .pptx (düzenlenebilir) hem .pdf (paylaşılabilir) hazır."*
- DE: *"Audit-Deck erstellt — Screenshots-Modus, beide Benchmark-Bereiche — 12 Folien, 2 Wichtig / 1 Mittel. Sowohl .pptx (bearbeitbar) als auch .pdf (zum Teilen) sind bereit."*

## Reference files

Load these when needed:

- **`references/adesso_layouts.md`** — full layout index, placeholder positions per layout, which layout to use for each slide type.
- **`references/qa_checklist.md`** — detailed visual QA process with grid-rendering command for fast overview inspection.
- **`scripts/pptx_helpers.py`** — the two critical patterns (scale-to-fit picture insertion, zip dedup). Import and use.
- **`assets/adesso_template.pptx`** — content-type-fixed copy of the adesso template as fallback if the user's version breaks.

# Adesso template — layout reference

The adesso template ships with 36 slide layouts. Only a subset are used by the audit deck. This file documents the ones we use and how their placeholders are addressed via python-pptx.

## Layout table

| Slide type | Layout index | Layout name | Notes |
|------------|--------------|-------------|-------|
| Cover | 2 | Titleslide BLUE | Full blue background, adesso logo top-right. Title placeholder idx=0, subtitle idx=1. |
| Overview | 14 | Title and Content WHITE | Title idx=0, body idx=17. Body accepts bullet list with bold labels. |
| Section divider | 8 | Section Header WHITE | Title idx=0, body idx=1. Large centered title, short subtitle. |
| Finding with screenshot | 20 | Content with Picture WHITE | Text left, picture right. Title idx=0, text body idx=1, picture placeholder idx=18. |
| Finding without screenshot | 14 | Title and Content WHITE | Same as Overview — used when finding has no accompanying screenshot. |
| Two-screenshot finding | 16 | Two Content WHITE | For rare cases needing two side-by-side images. Title idx=0, left body idx=1, right body idx=17. |
| Benchmark competitor slide with screenshot | 20 | Content with Picture WHITE | Same as finding-with-screenshot. |
| Benchmark competitor slide without screenshot | 14 | Title and Content WHITE | Text-only competitor description. |
| Benchmark market patterns | 14 | Title and Content WHITE | Can hold 3-5 market patterns in one slide. |
| Closing | 28 | Claim WHITE | Large centered text. Body idx=17. |

## Placeholder addressing quirks

Python-pptx addresses placeholders by their `placeholder_format.idx` (a stable integer, not their position on the slide). Layouts inherit placeholder definitions from their slide master, and the idx values follow the template's internal numbering — not a simple 0, 1, 2 sequence.

Always inspect the layout before assuming idx values:

```python
from pptx import Presentation
prs = Presentation('template_fixed.pptx')
for i, layout in enumerate(prs.slide_layouts):
    print(f"[{i}] {layout.name}")
    for ph in layout.placeholders:
        print(f"    idx={ph.placeholder_format.idx} name='{ph.name}'")
```

For the layouts above, the idx values have been verified against the adesso template as of the current bundled `adesso_template.pptx`. If the user provides a different or updated version of the template, re-verify.

## Setting text in a placeholder

```python
def set_title(slide, text):
    """Set the title placeholder (idx=0) text."""
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:
            ph.text_frame.text = text
            return

def set_body_lines(slide, ph_idx, lines):
    """Set multi-paragraph text in a body placeholder.
    `lines` is a list — each element is either a string (plain paragraph) 
    or a (label, text) tuple (bold label + body text).
    """
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == ph_idx:
            tf = ph.text_frame
            tf.clear()
            for i, item in enumerate(lines):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                if isinstance(item, tuple):
                    label, text = item
                    r1 = p.add_run(); r1.text = label + ': '; r1.font.bold = True
                    r2 = p.add_run(); r2.text = text
                else:
                    p.text = item
            return
```

## Adding a new slide with a layout

```python
def add_slide(prs, layout_idx):
    return prs.slides.add_slide(prs.slide_layouts[layout_idx])
```

## Deleting an existing slide

The template ships with 3 pre-populated demo slides. If you want a clean deck, you can either overwrite them (recommended for the first 2 — cover and overview) or delete them. **If you delete, you MUST run zip dedup** (see `scripts/pptx_helpers.py`) or the file will fail to render.

```python
def delete_slide(prs, slide_idx):
    xml_slides = prs.slides._sldIdLst
    slides_list = list(xml_slides)
    xml_slides.remove(slides_list[slide_idx])
```

## Recommended pattern for the audit deck

1. Open the template
2. Overwrite the first 2 pre-populated slides (cover, overview) with the audit's cover + overview content
3. Delete the 3rd pre-populated demo slide
4. Add new slides for section dividers, findings, benchmarks, closing
5. Save
6. Run zip dedup (required because we deleted slide 3)
7. Convert to PDF via LibreOffice for both delivery and QA

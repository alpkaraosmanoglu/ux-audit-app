# Visual QA checklist

After generating the .pptx and converting to .pdf, run a visual QA pass before delivery.

## Convert every slide to a JPEG

```bash
pdftoppm -jpeg -r 100 output_clean.pdf slide
```

This creates `slide-01.jpg`, `slide-02.jpg`, etc. — one per page of the PDF.

## Optional — grid render for fast overview

For a fast at-a-glance check, tile all slides into a single grid image:

```python
from PIL import Image
import glob

paths = sorted(glob.glob('slide-*.jpg'))
imgs = [Image.open(p) for p in paths]
w, h = imgs[0].size
sw, sh = w // 2, h // 2  # each thumbnail is half-size
cols = 5
rows = (len(imgs) + cols - 1) // cols
grid = Image.new('RGB', (sw * cols, sh * rows), 'white')
for i, img in enumerate(imgs):
    grid.paste(img.resize((sw, sh)), ((i % cols) * sw, (i // cols) * sh))
grid.save('all_slides_grid.jpg', quality=85)
```

Open `all_slides_grid.jpg` and scan for problems visible at thumbnail size — usually enough to catch the big defects.

## Defects to check

For each slide, verify:

**Title problems (most common):**
- ✗ Title wrapping to 3+ lines and visually overlapping the body text below it
- ✗ Title cut off mid-word at the placeholder edge
- Fix: shorten the finding title to ≤36 chars. This is a hard constraint.

**Body text problems:**
- ✗ Body text overflowing past the placeholder bottom (visible as text getting cut off)
- ✗ Text auto-shrinking below 12pt (unreadable in the room)
- Fix: shorten the finding body to under ~200 words, or split the finding across two slides.

**Screenshot problems:**
- ✗ Empty picture placeholder box on a layout-20 slide (screenshot not embedded)
- ✗ Screenshot overflowing past the slide's right edge
- ✗ Screenshot at wrong aspect ratio or cropped strangely
- Fix: verify the screenshot path is correct and `insert_image_fit()` was used (not `placeholder.insert_picture()`).

**Template leakage:**
- ✗ Leftover template placeholder text like "Title of the presentation", "Second level", "Text Stopper", "Edit text by clicking on it"
- ✗ Placeholder shapes visible as gray boxes
- Fix: locate the slide XML and either populate the placeholder or remove the shape.

**Language consistency:**
- ✗ Mixed language on any slide (e.g., "Overview" in English but the finding body in Turkish)
- Fix: verify every slide title, body label, and section header uses the audit's chosen language.

## The fix-and-verify cycle

Fix defects in the source code, regenerate the .pptx, re-dedup, re-convert to PDF, re-render slides. Do this **at most once** unless a genuinely new defect appears — infinite fix loops usually mean you're chasing symptoms rather than causes.

If after one fix cycle defects remain, ship the current version and note the defects to the user in the delivery message ("Slide 7 has a title-overflow issue I couldn't resolve — worth editing manually before presenting").

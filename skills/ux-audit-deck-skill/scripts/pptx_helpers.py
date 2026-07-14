"""Critical patterns for the UX audit deck skill.

Two functions here are essential and non-obvious:

1. insert_image_fit — python-pptx's default placeholder.insert_picture() crops/zooms wide
   screenshots past slide bounds, causing visible overflow past the slide edge. This helper
   removes the placeholder and inserts the image as a sized shape, preserving aspect ratio
   and centering within the original placeholder bounds.

2. dedup_zip — when slides are deleted from the template's sldIdLst or reordered via
   python-pptx, the original slide XML files stay in the zip even though they're no longer
   referenced. New slides added afterward can collide with the orphaned names, producing
   duplicate-name warnings on save and causing renderers (including LibreOffice) to reject
   the file with "source file could not be loaded." Run this pass after prs.save().
"""

from PIL import Image as PILImage
import zipfile


def insert_image_fit(slide, ph_idx, image_path):
    """Insert an image into a placeholder, scaled to fit while preserving aspect ratio.

    Removes the placeholder and inserts the image as a free-standing picture shape
    centered within the placeholder's original bounds. Do NOT use placeholder.insert_picture() —
    it crops and can overflow past the slide edge.

    Args:
        slide: python-pptx Slide object
        ph_idx: placeholder_format.idx of the picture placeholder to replace
        image_path: filesystem path to the image file

    Silently returns if the placeholder isn't found.
    """
    target_ph = next(
        (ph for ph in slide.placeholders if ph.placeholder_format.idx == ph_idx),
        None,
    )
    if target_ph is None:
        return

    ph_left, ph_top = target_ph.left, target_ph.top
    ph_w, ph_h = target_ph.width, target_ph.height

    with PILImage.open(image_path) as img:
        img_w, img_h = img.size

    scale = min(ph_w / img_w, ph_h / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)
    new_left = ph_left + (ph_w - new_w) // 2
    new_top = ph_top + (ph_h - new_h) // 2

    # Remove the placeholder so it doesn't render an empty box behind the image
    target_ph._element.getparent().remove(target_ph._element)

    slide.shapes.add_picture(image_path, new_left, new_top, new_w, new_h)


def dedup_zip(src_path, dst_path):
    """De-duplicate zip entries by keeping the LAST occurrence of each filename.

    Required after any operation that deletes or reorders slides via python-pptx.
    Without this, renderers reject the file with duplicate-name errors.

    Args:
        src_path: path to the pptx file produced by python-pptx (may contain duplicates)
        dst_path: path to write the deduped pptx file to

    The last-occurrence-wins strategy is correct because python-pptx writes updated
    slide XML AFTER the orphaned original XML in the archive, so the last copy is the
    valid current one.
    """
    with zipfile.ZipFile(src_path, "r") as zin:
        name_to_infos = {}
        for info in zin.infolist():
            name_to_infos.setdefault(info.filename, []).append(info)

        final = {}
        for name, infos in name_to_infos.items():
            chosen = infos[-1]  # last occurrence wins
            with zin.open(chosen) as f:
                final[name] = (chosen, f.read())

    with zipfile.ZipFile(dst_path, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, (info, data) in final.items():
            zout.writestr(info, data)


def set_title(slide, text):
    """Set the title placeholder (idx=0) text on a slide."""
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == 0:
            ph.text_frame.text = text
            return
    raise RuntimeError("No title placeholder (idx=0) on this slide")


def set_body_lines(slide, ph_idx, lines):
    """Set multi-paragraph text in a body placeholder.

    Args:
        slide: python-pptx Slide object
        ph_idx: placeholder_format.idx of the body placeholder
        lines: list where each element is either
            - a string (plain paragraph)
            - a (label, text) tuple (bold label + body text)
    """
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == ph_idx:
            tf = ph.text_frame
            tf.clear()
            for i, item in enumerate(lines):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                if isinstance(item, tuple):
                    label, text = item
                    r1 = p.add_run()
                    r1.text = label + ": "
                    r1.font.bold = True
                    r2 = p.add_run()
                    r2.text = text
                else:
                    p.text = item
            return
    raise RuntimeError(f"No placeholder at idx={ph_idx} on this slide")


def add_slide(prs, layout_idx):
    """Add a new slide using the given layout index."""
    return prs.slides.add_slide(prs.slide_layouts[layout_idx])


def delete_slide(prs, slide_idx):
    """Delete a slide by its position in the slide list.

    IMPORTANT: after any deletion, run dedup_zip() on the saved file — deleted slide XML
    stays in the archive and causes duplicate-name conflicts otherwise.
    """
    xml_slides = prs.slides._sldIdLst
    slides_list = list(xml_slides)
    xml_slides.remove(slides_list[slide_idx])

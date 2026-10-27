"""Circular arrow icons for the toolbar Undo / Redo buttons (drawn, no image files)."""
import math
from PIL import Image, ImageDraw


def circular_arrow(clockwise, size=24, colour=(230, 237, 245, 255), scale=4):
    """Like the arrow glyphs U+21BA / U+21BB: an open circle whose top end has an
    arrow head. clockwise=False -> Undo (head points left);
    clockwise=True -> Redo (head points right)."""
    big = size * scale
    image = Image.new('RGBA', (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    width = max(2, round(2.6 * scale))
    pad = 5 * scale
    box = (pad, pad + scale, big - pad, big - pad + scale)
    gap = 75                     # opening beside the arrow head
    if clockwise:                # opening at the top-right; head at the top pointing right
        start, end = 270 + gap, 270 + 360
    else:                        # opening at the top-left; head at the top pointing left
        start, end = 270, 270 - gap + 360
    draw.arc(box, start=start, end=end, fill=colour, width=width)
    cx = (box[0] + box[2]) / 2
    top = box[1] + width / 2
    head = 5.5 * scale
    direction = 1 if clockwise else -1
    tip = (cx + direction * head * 1.05, top)
    base = cx - direction * head * 0.25
    draw.polygon([tip, (base, top - head * 0.85), (base, top + head * 0.85)], fill=colour)
    return image.resize((size, size), Image.Resampling.LANCZOS)

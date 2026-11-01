"""Small PNG logos for the demo emails (Pillow). Deterministic: same bytes every run.

- acme_logo(): Acme Automotive's e-mail signature logo, sent inline as image001.png
  (under 10 KB, with a Content-ID). The intake must never read or store it.
- printhaus_logo(): the only content of PrintHaus's empty-subject mailing (logo.png, inline).
"""

import io

from PIL import Image, ImageDraw, ImageFont


def _png(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _font():
    return ImageFont.load_default()


def acme_logo():
    """160 x 40 px: a stylised road-and-wheel mark and the company name."""
    w, h = 160, 40
    img = Image.new("P", (w, h))
    img.putpalette([255, 255, 255, 0, 51, 102, 204, 0, 0, 120, 120, 120] + [0, 0, 0] * 252)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], fill=0)
    # mark: a dark-blue square with a red chevron
    d.rectangle([4, 4, 35, 35], fill=1)
    d.polygon([(10, 28), (20, 10), (30, 28), (25, 28), (20, 19), (15, 28)], fill=2)
    f = _font()
    d.text((42, 7), "ACME", fill=1, font=f)
    d.text((42, 21), "AUTOMOTIVE", fill=3, font=f)
    d.line([(42, 34), (150, 34)], fill=2, width=1)
    data = _png(img)
    assert len(data) < 10 * 1024, len(data)
    return data


def printhaus_logo():
    """240 x 70 px: the PrintHaus word mark on a coloured band."""
    w, h = 240, 70
    img = Image.new("P", (w, h))
    img.putpalette([255, 255, 255, 230, 120, 20, 40, 40, 40, 250, 220, 180] + [0, 0, 0] * 252)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], fill=0)
    d.rectangle([0, 0, w - 1, 14], fill=1)
    d.rectangle([0, h - 8, w - 1, h - 1], fill=3)
    f = _font()
    d.rectangle([14, 26, 40, 52], outline=2, width=2)
    d.rectangle([20, 32, 34, 46], fill=1)
    d.text((52, 26), "PrintHaus", fill=2, font=f)
    d.text((52, 40), "Druck & Medien", fill=1, font=f)
    return _png(img)

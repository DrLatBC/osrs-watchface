"""Renders text in the OSRS bitmap fonts from art/fonts (RuneStar's cache dumps).

Each glyph is a 1-bit bitmap placed on a line `ascent + maxDescent` pixels
tall; text gets the in-game 1-pixel black shadow down and to the right.
"""
import json
from functools import lru_cache
from pathlib import Path

from PIL import Image

FONTS = Path(__file__).resolve().parent / "fonts"
BLACK = (0, 0, 0, 255)


@lru_cache(maxsize=None)
def load(name):
    data = json.loads((FONTS / f"RuneScape-{name}.json").read_text())
    glyphs = {chr(g["codePoint"]): g for g in data["glyphs"]}
    return data["ascent"] + data["maxDescent"], glyphs


def _stamp(img, g, x0, color):
    px = img.load()
    w = g["width"]
    for i, on in enumerate(g["pixels"]):
        if on:
            px[x0 + g["leftBearing"] + i % w, g["topBearing"] + i // w] = color


def render(s, font, color, scale, band=None, cell=None):
    """The string as one image, at `scale` screen pixels per font pixel.

    band=(top, bottom) crops to those font rows so every image from one font
    shares a baseline. cell=w centres a single glyph's ink in a fixed w-pixel
    slot, for digit sets that must all be one width.
    """
    line_h, glyphs = load(font)
    if cell:
        g = glyphs[s]
        width, x0 = cell, (cell - g["width"]) // 2 - g["leftBearing"]
    else:
        width, x0 = sum(glyphs[c]["advance"] for c in s), 0
    img = Image.new("RGBA", (width + 1, line_h + 1), (0, 0, 0, 0))
    for pass_color, off in ((BLACK, 1), (color, 0)):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        x = x0
        for c in s:
            _stamp(layer, glyphs[c], x, pass_color)
            x += glyphs[c]["advance"]
        img.alpha_composite(layer, (off, off))
    if band:
        img = img.crop((0, band[0], img.width, band[1]))
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


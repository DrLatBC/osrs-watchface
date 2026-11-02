"""Draws every image the face uses, plus a composited mockup.

Run from the repo root:  python art/make_art.py
Writes assets/active2/images/**, art/mockup.png and watchface/layout.js (the
positions and image sizes the watch face code places widgets with), so the
mockup and the watch come from the same numbers. Text uses the real OSRS fonts (Bold-12 for
the time, Plain-11 for the rest); orbs and the potion are the in-game sprites
from art/sprites.
"""
import json
import math
import random
from pathlib import Path

from PIL import Image

import osrs_font

ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / "art" / "sprites"
IMAGES = ROOT / "assets" / "active2" / "images"
SIZE = 466
CENTER = SIZE / 2

CREAM = (242, 227, 179, 255)
GREEN = (62, 240, 62, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)

# Screen pixels per game pixel. Sprites, plates and small text share 2x so
# orbs and their numbers keep their in-game proportions; the time is 6x.
P, P_BIG = 2, 6

# Font rows kept for each text size, from the top of a digit down to the
# bottom of the shadow (small text keeps its descenders).
BIG_FONT, BIG_BAND, BIG_CELL = "Bold-12", (2, 13), 8
SMALL_FONT, SMALL_BAND, SMALL_CELL = "Plain-11", (1, 13), 6
BIG_BASELINE = (12 - BIG_BAND[0]) * P_BIG
SMALL_BASELINE = (9 - SMALL_BAND[0]) * P
SMALL_INK_H = 9 * P  # digit plus shadow
SMALL_DIGIT_W = (SMALL_CELL + 1) * P

DISC_R = 152  # dark inner circle
ORB_DIST, ORB_ANGLE = 134, 47  # orb centres, from the face centre


def big(s):
    return osrs_font.render(s, BIG_FONT, CREAM, P_BIG, BIG_BAND, BIG_CELL if s.isdigit() else None)


def small(s, color):
    return osrs_font.render(s, SMALL_FONT, color, P, SMALL_BAND, SMALL_CELL if s.isdigit() else None)


def sprite(name, frame=0, scale=P):
    im = Image.open(SPRITES / name)
    im.seek(frame)
    im = im.convert("RGBA")
    im = im.crop(im.getbbox())
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


# ---------------------------------------------------------------- textures

def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3]) + (255,)


def stones():
    """Random-bond castle stonework: courses of mixed-length blocks, some
    split into two smaller stones, each lit from the top left."""
    a = SIZE // P + 1
    rnd = random.Random(11)
    img = Image.new("RGBA", (a, a), (22, 22, 25, 255))
    px = img.load()
    blocks = []
    y = 0
    while y < a:
        h = rnd.randint(10, 15)
        x = -rnd.randint(0, 10)
        while x < a:
            w = rnd.randint(12, 28)
            if h >= 12 and rnd.random() < 0.3:
                top = rnd.randint(5, h - 5)
                split = rnd.randint(5, w - 5) if w >= 16 else None
                blocks.append((x, y, w, top))
                if split:
                    blocks += [(x, y + top, split, h - top), (x + split, y + top, w - split, h - top)]
                else:
                    blocks.append((x, y + top, w, h - top))
            else:
                blocks.append((x, y, w, h))
            x += w
        y += h
    for x0, y0, w, h in blocks:
        g = rnd.randint(66, 92)
        base = (g + 3, g, g - 2, 255)
        # A gap of one pixel on the right and bottom of every stone, so
        # neighbours read as separate blocks.
        iw, ih = w - 1, h - 1
        for ly in range(ih):
            for lx in range(iw):
                x, y = x0 + lx, y0 + ly
                if not (0 <= x < a and 0 <= y < a):
                    continue
                corner = (lx in (0, iw - 1)) and (ly in (0, ih - 1))
                if corner:
                    continue
                if ly == 0 or lx == 0:
                    c = shade(base, 1.28)
                elif ly == ih - 1 or lx == iw - 1:
                    c = shade(base, 0.62)
                elif ly == ih - 2 or lx == iw - 2:
                    c = shade(base, 0.82)
                else:
                    r = rnd.random()
                    c = shade(base, 0.86) if r < 0.14 else shade(base, 1.1) if r < 0.22 else base
                px[x, y] = c
    img = img.resize((a * P, a * P), Image.NEAREST)
    return img.crop((0, 0, SIZE, SIZE))


# Cross-section of the metal pipe, outer edge to outer edge, in game pixels.
PIPE = [(16, 15, 19), (60, 57, 68), (86, 82, 96), (114, 110, 126),
        (132, 128, 144), (104, 100, 116), (74, 71, 84), (16, 15, 19)]
KNOB_R = 5.5   # ball joints, game pixels
RING_KNOBS = 4
FRAME_MARGIN = 3  # room for the corner joints to stick out past a pipe frame


def knob(px, cx, cy, r=KNOB_R):
    """A ball joint lit from the top left, centred at game pixel (cx, cy)."""
    for y in range(int(cy - r) - 1, int(cy + r) + 2):
        for x in range(int(cx - r) - 1, int(cx + r) + 2):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            d = math.hypot(dx, dy)
            if d > r:
                continue
            if d > r - 1:
                c = PIPE[0]
            else:
                nz = math.sqrt(max(0.0, 1 - (d / r) ** 2))
                i = max(0.0, -0.5 * dx / r - 0.55 * dy / r + 0.67 * nz)
                g = int(40 + 110 * i)
                c = (g, g - 3, g + 10)
            px[x, y] = c + (255,)


def game_layer():
    n = SIZE // P + 1
    return Image.new("RGBA", (n, n), (0, 0, 0, 0))


def to_screen(layer):
    return layer.resize((layer.width * P, layer.height * P), Image.NEAREST).crop((0, 0, SIZE, SIZE))


def disc(img):
    """Near-black inner circle inside a pipe ring with ball joints."""
    layer = game_layer()
    px = layer.load()
    c, r0 = CENTER / P, DISC_R / P
    for gy in range(layer.height):
        for gx in range(layer.width):
            d = math.hypot(gx + 0.5 - c, gy + 0.5 - c)
            if d < r0:
                px[gx, gy] = (16, 16, 18, 255)
            elif d < r0 + len(PIPE):
                px[gx, gy] = PIPE[int(d - r0)] + (255,)
    mid = r0 + len(PIPE) / 2
    for k in range(RING_KNOBS):
        a = 2 * math.pi * k / RING_KNOBS
        knob(px, c + mid * math.cos(a), c + mid * math.sin(a))
    img.alpha_composite(to_screen(layer))


def pipe_frame(w, h):
    """Dark panel framed by the ring's pipe, with ball joints at the corners;
    w x h in game pixels including the frame."""
    n = len(PIPE)
    m = FRAME_MARGIN
    layer = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
    px = layer.load()
    for y in range(h):
        for x in range(w):
            edge = min(x, y, w - 1 - x, h - 1 - y)
            if edge >= n:
                c = (16, 16, 18)
            elif min(y, h - 1 - y) < n and (min(x, w - 1 - x) >= min(y, h - 1 - y)):
                c = PIPE[y if y < n else n - 1 - (h - 1 - y)]
            else:
                c = PIPE[x if x < n else n - 1 - (w - 1 - x)]
            px[x + m, y + m] = c + (255,)
    for cx in (m + n / 2, m + w - n / 2):
        for cy in (m + n / 2, m + h - n / 2):
            knob(px, cx, cy, KNOB_R + 0.5)
    return layer.resize((layer.width * P, layer.height * P), Image.NEAREST)


def slab(w, h):
    """Grey bevelled plaque, w x h in game pixels."""
    img = Image.new("RGBA", (w, h), (62, 60, 64, 255))
    px = img.load()
    for y in range(h):
        for x in range(w):
            if x in (0, w - 1) or y in (0, h - 1):
                px[x, y] = (6, 6, 6, 255)
            elif x == 1 or y == 1:
                px[x, y] = (118, 116, 120, 255)
            elif x == w - 2 or y == h - 2:
                px[x, y] = (28, 28, 30, 255)
    return img.resize((w * P, h * P), Image.NEAREST)


# ---------------------------------------------------------------- layout

PLATE_H = 2 + 3 + 9 + 3 + 2  # border, pad, digit+shadow, pad, border
PLATE_PAD = 4                # game pixels between text and the plate's outer end

_dx = round(ORB_DIST * math.cos(math.radians(ORB_ANGLE)))
_dy = round(ORB_DIST * math.sin(math.radians(ORB_ANGLE)))
ORBS = {
    "hp": (CENTER - _dx, CENTER - _dy, "left", 3),
    "prayer": (CENTER + _dx, CENTER - _dy, "right", 3),
    "run": (CENTER - _dx, CENTER + _dy, "left", 5),
    "globe": (CENTER + _dx, CENTER + _dy, "right", 4),
}
ORB_HALF = 34  # half the 68 px orb sprite
ORB_GAP = 2 * P  # between an orb's rim and its number


def plate_box(cx, cy, side, cells):
    """A plate running outward from under an orb; its text sits against the orb."""
    text_w = cells * SMALL_DIGIT_W
    hpx = PLATE_H * P
    if side == "left":
        text_x = cx - ORB_HALF - ORB_GAP - text_w
        x0 = text_x - (PLATE_PAD + 2) * P
        x1 = cx
    else:
        text_x = cx + ORB_HALF + ORB_GAP
        x0 = cx
        x1 = text_x + text_w + (PLATE_PAD + 2) * P
    return {"x": int(x0), "y": int(cy - hpx / 2), "w": int(x1 - x0), "h": hpx,
            "text": {"x": int(text_x), "y": int(cy - SMALL_INK_H / 2), "w": int(text_w),
                     "align": side == "left" and "right" or "left"}}


LAYOUT = {
    "plates": {k: plate_box(*v) for k, v in ORBS.items()},
    "orbs": {k: {"cx": v[0], "cy": v[1]} for k, v in ORBS.items()},
    "compass": {"cx": CENTER, "cy": CENTER - DISC_R - len(PIPE) * P / 2},
    "time": {"y": 181},
    "date": {"y": 259},
    "battery": {"cy": CENTER + DISC_R + len(PIPE) * P / 2},
}

# Tapping the globe orb or its temperature plate opens the weather app.
_globe, _globe_plate = LAYOUT["orbs"]["globe"], LAYOUT["plates"]["globe"]
LAYOUT["tap"] = {"globe": {
    "x": int(_globe["cx"] - ORB_HALF),
    "y": int(_globe["cy"] - ORB_HALF),
    "w": int(_globe_plate["x"] + _globe_plate["w"] - (_globe["cx"] - ORB_HALF)),
    "h": 2 * ORB_HALF,
}}


def check_fit():
    """Every plate's text must sit inside the round screen with a margin."""
    for key, p in LAYOUT["plates"].items():
        t = p["text"]
        for x in (t["x"], t["x"] + t["w"]):
            for y in (t["y"], t["y"] + SMALL_INK_H):
                r = math.hypot(x - CENTER, y - CENTER)
                assert r < CENTER - 6, f"{key} text corner ({x},{y}) is {r:.0f} px from centre"


# ---------------------------------------------------------------- orb fills

FILL_STEPS = 20  # images per orb: 0%, 5%, ... 100%
ORB_C, ORB_IN = 17, 13.1  # sprite centre and inner radius of its frame


def orb_fills(name, frame=0):
    """The official orb at every fill level. The fill is the part of the
    orb's inside reachable from its rim without crossing the icon's black
    outline; above the level line it is darkened to the empty orb."""
    im = Image.open(SPRITES / name)
    im.seek(frame)
    im = im.convert("RGBA")
    px = im.load()

    def inside(x, y):
        return math.hypot(x + 0.5 - ORB_C, y + 0.5 - ORB_C) < ORB_IN

    def open_px(x, y):
        return inside(x, y) and max(px[x, y][:3]) > 12

    seen = set()
    stack = [(x, y) for y in range(im.height) for x in range(im.width)
             if open_px(x, y) and math.hypot(x + 0.5 - ORB_C, y + 0.5 - ORB_C) > ORB_IN - 1.5]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen:
            continue
        seen.add((x, y))
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < im.width and 0 <= ny < im.height and (nx, ny) not in seen and open_px(nx, ny):
                stack.append((nx, ny))

    top, bottom = ORB_C - ORB_IN, ORB_C + ORB_IN
    out = []
    for step in range(FILL_STEPS + 1):
        line = bottom - (bottom - top) * step / FILL_STEPS
        o = im.copy()
        op = o.load()
        for x, y in seen:
            if y + 0.5 < line:
                r, g, b, a = op[x, y]
                l = int((r + g + b) / 3 * 0.25)
                op[x, y] = (l, l, l + 2, a)
        out.append(o.resize((o.width * P, o.height * P), Image.NEAREST))
    return out


COMPASS_STEPS = 36  # dial images, 10 degrees apart
COMPASS_DIAL_R = 16.6  # game pixels; the rim outside this stays fixed


def compass_frames():
    """The minimap compass with its dial turned anticlockwise by 0, 10, ...
    350 degrees, so a heading of h degrees shows frame round(h / 10). The
    dial is turned at 8x and sampled back down so it stays pixel-crisp."""
    im = Image.open(SPRITES / "Compass.png").convert("RGBA")
    n, c = im.width, im.width / 2
    big = im.resize((n * 8, n * 8), Image.NEAREST)
    out = []
    for k in range(COMPASS_STEPS):
        turned = big.rotate(k * 360 / COMPASS_STEPS, resample=Image.NEAREST).resize((n, n), Image.NEAREST)
        o = im.copy()
        op, tp = o.load(), turned.load()
        for y in range(n):
            for x in range(n):
                if math.hypot(x + 0.5 - c, y + 0.5 - c) < COMPASS_DIAL_R:
                    op[x, y] = tp[x, y]
        out.append(o.resize((n * P, n * P), Image.NEAREST))
    return out


# ---------------------------------------------------------------- output

SIZES = {}  # every saved image's [w, h], keyed by its path on the watch


def save(img, rel):
    path = IMAGES / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    SIZES["images/" + rel] = [img.width, img.height]
    return img


def build_sprites():
    s = {"big": {d: save(big(d), f"big/{d}.png") for d in "0123456789"}}
    s["big"][":"] = save(big(":"), "big/colon.png")
    for name, color in (("green", GREEN), ("cream", CREAM), ("white", WHITE)):
        s[name] = {d: save(small(d, color), f"{name}/{d}.png") for d in "0123456789"}
    s["green"]["-"] = save(small("-", GREEN), "green/minus.png")
    s["green"]["°"] = save(small("°", GREEN), "green/degree.png")
    s["white"]["%"] = save(small("%", WHITE), "white/percent.png")
    s["cream"]["-"] = save(small("-", CREAM), "cream/dash.png")
    days = ["Mon,", "Tue,", "Wed,", "Thu,", "Fri,", "Sat,", "Sun,"]
    s["week"] = [save(small(d, CREAM), f"week/{i}.png") for i, d in enumerate(days)]
    s["am"] = save(small("am", CREAM), "ampm/am.png")
    s["pm"] = save(small("pm", CREAM), "ampm/pm.png")
    s["fills"] = {}
    for key, name in (("hp", "Hitpoints_orb.png"), ("prayer", "Prayer_orb.png"), ("run", "Run_energy_orb.gif")):
        s["fills"][key] = [save(im, f"orbs/{key}/{i}.png") for i, im in enumerate(orb_fills(name))]
    s["globe"] = sprite("World_map_icon.png")
    s["compass"] = [save(im, f"compass/{i}.png") for i, im in enumerate(compass_frames())]
    t = LAYOUT["tap"]["globe"]
    save(Image.new("RGBA", (t["w"], t["h"]), (0, 0, 0, 0)), "tap/globe.png")
    # The potion is drawn at 1x so it fits a plaque the height of the orb plates.
    s["potion"] = sprite("potions/Antipoison(4).png", scale=1)
    return s


def build_background(s):
    bg = stones()
    disc(bg)
    for p in LAYOUT["plates"].values():
        bg.alpha_composite(slab(p["w"] // P, PLATE_H), (p["x"], p["y"]))
    put_orb(bg, "globe", s["globe"])
    bat = battery_plaque(s)
    bg.alpha_composite(bat, (LAYOUT["battery"]["x"], LAYOUT["battery"]["y"]))
    return save(bg, "bg.png")


def put_orb(canvas, key, im):
    o = LAYOUT["orbs"][key]
    canvas.alpha_composite(im, (int(o["cx"] - im.width / 2), int(o["cy"] - im.height / 2)))


def battery_plaque(s):
    """Potion and "100%" in a pipe-framed panel, centred on the bottom of the ring."""
    pot = s["potion"]
    n = len(PIPE)
    text_w = 3 * SMALL_DIGIT_W + s["white"]["%"].width
    pot_w, pot_h = -(-pot.width // P), -(-pot.height // P)
    w = n + 3 + pot_w + 3 + text_w // P + 3 + n
    h = n + 2 + pot_h + 2 + n
    img = pipe_frame(w, h)
    img.alpha_composite(pot, ((FRAME_MARGIN + n + 3) * P, (img.height - pot.height) // 2))
    b = LAYOUT["battery"]
    b.update({"x": int(CENTER - img.width / 2), "y": int(b["cy"] - img.height / 2),
              "w": img.width, "h": img.height})
    b["text"] = {"x": b["x"] + (FRAME_MARGIN + n + 3 + pot_w + 3) * P, "w": text_w,
                 "y": int(b["cy"] - SMALL_INK_H / 2)}
    return img


def row_width(parts):
    return sum(p.width for p in parts)


def place_text(canvas, parts, x, y):
    for p in parts:
        canvas.alpha_composite(p, (int(x), int(y)))
        x += p.width
    return x


def mockup(bg, s):
    m = bg.copy()
    # The block is centred for a two-digit hour; the hour is right-aligned
    # against the colon so the colon and minutes never move.
    b = s["big"]
    pm = s["pm"]
    digit_w, colon_w, gap = b["0"].width, b[":"].width, 2 * P
    t = LAYOUT["time"]
    t["hour_x"] = int(CENTER - (4 * digit_w + colon_w + gap + pm.width) / 2)
    t["colon_x"] = t["hour_x"] + 2 * digit_w
    t["minute_x"] = t["colon_x"] + colon_w
    t["ampm_x"] = t["minute_x"] + 2 * digit_w + gap
    t["ampm_y"] = t["y"] + BIG_BASELINE - SMALL_BASELINE
    place_text(m, [b["1"]], t["colon_x"] - digit_w, t["y"])
    place_text(m, [b[":"], b["5"], b["2"]], t["colon_x"], t["y"])
    m.alpha_composite(pm, (t["ampm_x"], t["ampm_y"]))

    c = s["cream"]
    day = s["week"][4]
    date = [c["1"], c["0"], c["-"], c["3"], c["0"], c["-"], c["2"], c["0"], c["2"], c["6"]]
    secs = [c["3"], c["3"]]
    space, secs_gap = 3 * P, 8 * P
    full = day.width + space + row_width(date) + secs_gap + row_width(secs)
    d = LAYOUT["date"]
    d.update({"space": space, "secs_gap": secs_gap})
    x = place_text(m, [day], CENTER - full / 2, d["y"]) + space
    x = place_text(m, date, x, d["y"])
    place_text(m, secs, x + secs_gap, d["y"])

    for key, step in (("hp", 18), ("prayer", 16), ("run", 17)):
        put_orb(m, key, s["fills"][key][step])
    cp = LAYOUT["compass"]
    dial = s["compass"][0]
    m.alpha_composite(dial, (int(cp["cx"] - dial.width / 2), int(cp["cy"] - dial.height / 2)))

    g = s["green"]
    for key, value in (("hp", "72"), ("prayer", "97"), ("run", "12843"), ("globe", "18°")):
        tb = LAYOUT["plates"][key]["text"]
        parts = [g[ch] for ch in value]
        x = tb["x"] + tb["w"] - row_width(parts) if tb["align"] == "right" else tb["x"]
        place_text(m, parts, x, tb["y"])

    bt = LAYOUT["battery"]["text"]
    w = s["white"]
    parts = [w["8"], w["4"], w["%"]]
    place_text(m, parts, bt["x"] + (bt["w"] - row_width(parts)) / 2, bt["y"])
    return m


def main():
    check_fit()
    s = build_sprites()
    bg = build_background(s)
    m = mockup(bg, s)
    screen = Image.new("L", m.size, 0)
    sp = screen.load()
    for y in range(SIZE):
        for x in range(SIZE):
            if math.hypot(x + 0.5 - CENTER, y + 0.5 - CENTER) <= CENTER:
                sp[x, y] = 255
    shown = Image.composite(m, Image.new("RGBA", m.size, BLACK), screen)
    shown.convert("RGB").save(ROOT / "art" / "mockup.png")
    save(shown.resize((PREVIEW, PREVIEW), Image.LANCZOS), "preview.png")
    write_layout()


PREVIEW = 314  # the Active 2's watch face preview size


def write_layout():
    consts = {"SIZE": SIZE, "CENTER": CENTER, "FILL_STEPS": FILL_STEPS, "COMPASS_STEPS": COMPASS_STEPS}
    lines = ["// Generated by art/make_art.py; edit that, not this.", ""]
    lines += [f"export const {k} = {json.dumps(v)}" for k, v in consts.items()]
    lines += [f"export const LAYOUT = {json.dumps(LAYOUT, indent=2)}", "",
              f"export const SIZES = {json.dumps(SIZES, indent=2, sort_keys=True)}", ""]
    (ROOT / "watchface" / "layout.js").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

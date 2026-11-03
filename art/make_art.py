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

import numpy as np
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
GOLD = (255, 214, 64, 255)   # sunrise time
DUSK = (255, 140, 32, 255)   # sunset time

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


# Sunrise and sunset times sit in the stonework just outside the ring's 9 and
# 3 o'clock joints, each against its joint, with a horizon icon centred above.
TRACK_R = DISC_R + len(PIPE) * P / 2  # the pipe's centre line
LABEL_W = 3 * SMALL_DIGIT_W + small(":", CREAM).width  # "h:mm" fills the box exactly
HORIZON_W, HORIZON_H = 13, 12  # icon ink, game pixels; the shadow adds one each way
_joint_out = CENTER - TRACK_R - KNOB_R * P
_label_y = int(CENTER - SMALL_INK_H / 2)
LAYOUT["sky"] = {
    "rise": {"x": int(_joint_out - 2 * P - LABEL_W), "y": _label_y, "w": LABEL_W, "align": "right"},
    "set": {"x": int(SIZE - _joint_out + 2 * P), "y": _label_y, "w": LABEL_W, "align": "left"},
}
for _box in LAYOUT["sky"].values():
    _iw, _ih = (HORIZON_W + 1) * P, (HORIZON_H + 1) * P
    _box["icon"] = [int(_box["x"] + (_box["w"] - _iw) / 2), _label_y - _ih - P]


def check_fit():
    """Every plate's text and the sky labels and icons must sit inside the
    round screen with a margin."""
    boxes = {k: (p["text"]["x"], p["text"]["y"], p["text"]["w"], SMALL_INK_H) for k, p in LAYOUT["plates"].items()}
    for key in ("rise", "set"):
        b = LAYOUT["sky"][key]
        boxes[key] = (b["x"], b["y"], b["w"], SMALL_INK_H)
        boxes[key + " icon"] = (*b["icon"], (HORIZON_W + 1) * P, (HORIZON_H + 1) * P)
    for key, (bx, by, bw, bh) in boxes.items():
        for x in (bx, bx + bw):
            for y in (by, by + bh):
                r = math.hypot(x - CENTER, y - CENTER)
                assert r < CENTER - 6, f"{key} corner ({x},{y}) is {r:.0f} px from centre"


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


# ---------------------------------------------------------------- sky

BODY = 17             # sun and moon, game pixels across
BODY_HALF = BODY * P // 2
MOON_PHASES = 8       # new, waxing crescent, first quarter, ... waning crescent
GLOW_FRAMES = 12      # per thing the sun or moon passes behind
GLOW_W = 14           # screen pixels the light reaches past an edge, at the tip of a sun ray
GLOW_REACH = 72       # screen pixels past the body's rim where the light fades out
SUN_RAYS = 16
GLOW_ALPHA = [0, 120, 170, 215, 255]  # by level, 0 = none
LIGHT = {  # level 4 first
    "sun": [(255, 250, 200), (255, 232, 120), (255, 200, 70), (240, 160, 40)],
    "moon": [(240, 244, 255), (210, 222, 255), (176, 194, 245), (140, 160, 225)],
}


def track(body, a):
    """Screen position a degrees along the body's half of the ring: the sun
    runs 9 -> 12 -> 3 o'clock from sunrise to sunset, the moon 3 -> 6 -> 9
    from sunset to sunrise. watchface/index.js has the same function."""
    t = math.radians(a)
    if body == "sun":
        return CENTER - TRACK_R * math.cos(t), CENTER - TRACK_R * math.sin(t)
    return CENTER + TRACK_R * math.cos(t), CENTER + TRACK_R * math.sin(t)


def js_round(v):
    return math.floor(v + 0.5)


def body_xy(body, a):
    """Top-left of the body's image, rounded the way the face rounds it."""
    x, y = track(body, a)
    return js_round(x - BODY_HALF), js_round(y - BODY_HALF)


def sun_sprite():
    c = BODY / 2
    img = Image.new("RGBA", (BODY, BODY), (0, 0, 0, 0))
    px = img.load()
    for y in range(BODY):
        for x in range(BODY):
            dx, dy = x + 0.5 - c, y + 0.5 - c
            d = math.hypot(dx, dy)
            if d > c:
                continue
            if d > c - 1:
                col = (120, 56, 8)
            else:
                i = -0.45 * dx / c - 0.5 * dy / c
                col = (255, 240, 150) if i > 0.3 else (255, 206, 64) if i > -0.2 else (236, 150, 28)
            px[x, y] = col + (255,)
    return img.resize((BODY * P, BODY * P), Image.NEAREST)


HORIZON_SUN = {  # light to dark
    "rise": [(255, 240, 150), (255, 206, 64), (236, 150, 28)],
    "set": [(255, 200, 120), (255, 140, 40), (210, 80, 24)],
}


def horizon_icon(key):
    """A half sun on the horizon under an arrow, up for sunrise and down for
    sunset, with the OSRS one-pixel black shadow."""
    w, h = HORIZON_W, HORIZON_H
    ink = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = ink.load()
    head = [[6], [5, 6, 7], [4, 5, 6, 7, 8], [3, 4, 5, 6, 7, 8, 9]]
    arrow = head + [[6]] if key == "rise" else [[6]] + head[::-1]
    for y, xs in enumerate(arrow):
        for x in xs:
            px[x, y] = CREAM
    pal = HORIZON_SUN[key]
    for y in range(6, 11):
        for x in range(w):
            d = math.hypot(x + 0.5 - 6.5, y + 0.5 - 11)
            if d <= 4.6:
                px[x, y] = (pal[0] if d < 2.4 else pal[1] if d < 3.7 else pal[2]) + (255,)
    for x, y in ((0, 9), (1, 9), (11, 9), (12, 9), (2, 6), (10, 6)):
        px[x, y] = pal[1] + (255,)
    for x in range(w):
        px[x, h - 1] = CREAM
    out = Image.new("RGBA", (w + 1, h + 1), (0, 0, 0, 0))
    out.paste(Image.new("RGBA", (w, h), BLACK), (1, 1), ink)
    out.alpha_composite(ink)
    return out.resize((out.width * P, out.height * P), Image.NEAREST)


MOON_CRATERS ={(5, 5), (6, 5), (5, 6), (10, 8), (11, 8), (11, 9), (5, 11), (9, 13), (10, 13), (12, 4)}


def moon_phases():
    """The moon lit as seen from the northern hemisphere: frame k is k/8 of
    the way from one new moon to the next, full at 4."""
    c = BODY / 2
    out = []
    for k in range(MOON_PHASES):
        p = k / MOON_PHASES
        img = Image.new("RGBA", (BODY, BODY), (0, 0, 0, 0))
        px = img.load()
        for y in range(BODY):
            for x in range(BODY):
                dx, dy = x + 0.5 - c, y + 0.5 - c
                d = math.hypot(dx, dy)
                if d > c:
                    continue
                if d > c - 1:
                    col = (20, 22, 30)
                else:
                    w = math.sqrt(max(0.0, 1 - (dy / c) ** 2))
                    edge = w * math.cos(2 * math.pi * p)
                    u = dx / c
                    lit = u > edge if p < 0.5 else u < -edge
                    if lit:
                        col = (190, 190, 180) if (x, y) in MOON_CRATERS else (228, 228, 216)
                    else:
                        col = (74, 80, 104)
                px[x, y] = col + (255,)
        out.append(img.resize((BODY * P, BODY * P), Image.NEAREST))
    return out


def alpha_mask(im, x, y):
    m = np.zeros((SIZE, SIZE), bool)
    a = np.array(im)[:, :, 3] > 0
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(SIZE, x + im.width), min(SIZE, y + im.height)
    m[y0:y1, x0:x1] = a[y0 - y:y1 - y, x0 - x:x1 - x]
    return m


def shifted(m, dx, dy):
    """out[y, x] = m[y + dy, x + dx], False off the edge."""
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)] = \
        m[max(0, dy):h - max(0, -dy), max(0, dx):w - max(0, -dx)]
    return out


def edge_distance(mask):
    """Distance from each pixel to the nearest masked pixel, up to GLOW_W."""
    e = np.full(mask.shape, np.inf)
    e[mask] = 0
    for dy in range(-GLOW_W, GLOW_W + 1):
        for dx in range(-GLOW_W, GLOW_W + 1):
            r = math.hypot(dx, dy)
            if 0 < r <= GLOW_W:
                e = np.where(shifted(mask, dx, dy), np.minimum(e, r), e)
    return e


def occluders(s):
    """What the sun and moon pass behind, as screen masks: each orb with its
    plate, the compass and the battery plaque."""
    def placed(im, cx, cy):
        return alpha_mask(im, int(cx - im.width / 2), int(cy - im.height / 2))

    groups = {}
    for key, body in (("hp", "sun"), ("prayer", "sun"), ("run", "moon"), ("globe", "moon")):
        o, p = LAYOUT["orbs"][key], LAYOUT["plates"][key]
        im = s["globe"] if key == "globe" else s["fills"][key][FILL_STEPS]
        m = placed(im, o["cx"], o["cy"])
        m[p["y"]:p["y"] + p["h"], p["x"]:p["x"] + p["w"]] = True
        groups[key] = (body, m)
    cp = LAYOUT["compass"]
    groups["compass"] = ("sun", placed(s["compass"][0], cp["cx"], cp["cy"]))
    b = LAYOUT["battery"]
    groups["plaque"] = ("moon", alpha_mask(s["plaque"], b["x"], b["y"]))
    return groups


def covered(mask, body, a):
    x, y = body_xy(body, a)
    disc = alpha_mask(SKY_DISC, x, y)
    return (mask & disc).sum() / SKY_DISC_AREA


SKY_DISC = sun_sprite()
SKY_DISC_AREA = int((np.array(SKY_DISC)[:, :, 3] > 0).sum())


def glow(mask, e, body, a):
    """Light leaking around the edges of mask from the body at a degrees,
    brighter nearer the body and stronger the more of it is hidden. Worked
    out per game pixel so it stays blocky, then trimmed off the mask."""
    h = covered(mask, body, a)
    if h <= 0:
        return None
    bx, by = track(body, a)
    ys, xs = np.mgrid[0:SIZE, 0:SIZE]
    gx, gy = (xs // P) * P + P / 2, (ys // P) * P + P / 2  # each pixel's game-pixel centre
    eg = e[(gy).astype(int), (gx).astype(int)]
    near = (1 - np.clip((np.hypot(gx - bx, gy - by) - BODY_HALF) / GLOW_REACH, 0, 1)) ** 0.6
    if body == "sun":
        # A short halo all round, with thin rays out to the full reach.
        spike = np.maximum(0, np.cos(SUN_RAYS * np.arctan2(gy - by, gx - bx))) ** 3
        reach = GLOW_W * (0.45 + 0.55 * spike)
    else:
        reach = GLOW_W * 0.7
    rim = np.where(np.isfinite(eg), np.clip(1 - eg / (reach + 1), 0, 1), 0)
    v = rim * near * min(1.0, h / 0.4)
    level = np.ceil(v * 4 - 0.25).clip(0, 4).astype(int)
    level[mask] = 0
    if not level.any():
        return None
    out = np.zeros((SIZE, SIZE, 4), np.uint8)
    for n, col in zip((4, 3, 2, 1), LIGHT[body]):
        sel = level == n
        out[sel, :3] = col
        out[sel, 3] = GLOW_ALPHA[n]
    img = Image.fromarray(out)
    box = img.getbbox()
    return img.crop(box), box[0], box[1]


def build_sky(s):
    """Glow frames for each occluder over the stretch of track where it hides
    part of the body, and their positions for the face."""
    sky = LAYOUT["sky"]
    sky.update({"cx": CENTER, "cy": CENTER, "r": TRACK_R, "half": BODY_HALF, "glows": {}})
    s["glows"] = {}
    for key, (body, mask) in occluders(s).items():
        hidden = [a / 4 for a in range(0, 721) if covered(mask, body, a / 4) > 0]
        a0, a1 = hidden[0], hidden[-1]
        e = edge_distance(mask)
        frames, imgs = [], []
        for i in range(GLOW_FRAMES):
            g = glow(mask, e, body, a0 + (a1 - a0) * i / (GLOW_FRAMES - 1))
            if g is None:
                frames.append(None)
                imgs.append(None)
                continue
            img, x, y = g
            save(img, f"glow/{key}/{i}.png")
            frames.append([x, y])
            imgs.append((img, x, y))
        sky["glows"][key] = {"body": body, "a0": a0, "a1": a1, "frames": frames}
        s["glows"][key] = imgs


def glow_frame(g, a):
    """The glow frame index for a degrees along the track, or None outside
    the occluder's stretch. watchface/index.js picks frames the same way."""
    if not g["a0"] <= a <= g["a1"]:
        return None
    return js_round((a - g["a0"]) / (g["a1"] - g["a0"]) * (GLOW_FRAMES - 1))


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
    for name, color in (("gold", GOLD), ("dusk", DUSK)):
        s[name] = {d: save(small(d, color), f"{name}/{d}.png") for d in "0123456789"}
        s[name][":"] = save(small(":", color), f"{name}/colon.png")
    s["horizon"] = {k: save(horizon_icon(k), f"sky/{k}.png") for k in ("rise", "set")}
    s["sun"] = save(sun_sprite(), "sky/sun.png")
    s["moon"] = [save(im, f"sky/moon/{i}.png") for i, im in enumerate(moon_phases())]
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
    """The background, plus copies of the parts baked into it that the sun
    and moon pass behind (plates, the globe, the battery plaque), which the
    face lays back over them."""
    bg = stones()
    disc(bg)
    over = []
    for key, p in LAYOUT["plates"].items():
        over.append((save(slab(p["w"] // P, PLATE_H), f"over/plate_{key}.png"), p["x"], p["y"]))
    g, o = s["globe"], LAYOUT["orbs"]["globe"]
    over.append((save(g, "over/globe.png"), int(o["cx"] - g.width / 2), int(o["cy"] - g.height / 2)))
    s["plaque"] = battery_plaque(s)
    over.append((save(s["plaque"], "over/plaque.png"), LAYOUT["battery"]["x"], LAYOUT["battery"]["y"]))
    for im, x, y in over:
        bg.alpha_composite(im, (x, y))
    s["over"] = over
    names = [f"plate_{k}" for k in LAYOUT["plates"]] + ["globe", "plaque"]
    LAYOUT["sky"]["over"] = [[f"images/over/{n}.png", x, y] for n, (_, x, y) in zip(names, over)]
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


def draw_sky(m, s, sky):
    """The sun or moon at sky["a"] degrees along its track, with the glows,
    the overlays it hides behind and the sunrise and sunset times, layered
    as the face layers them."""
    body = sky["body"]
    for key, g in LAYOUT["sky"]["glows"].items():
        i = glow_frame(g, sky["a"]) if g["body"] == body else None
        if i is not None and s["glows"][key][i]:
            img, x, y = s["glows"][key][i]
            m.alpha_composite(img, (x, y))
    im = s["sun"] if body == "sun" else s["moon"][sky["phase"]]
    m.alpha_composite(im, body_xy(body, sky["a"]))
    for im, x, y in s["over"]:
        m.alpha_composite(im, (x, y))
    for key, font in (("rise", s["gold"]), ("set", s["dusk"])):
        box, parts = LAYOUT["sky"][key], [font[ch] for ch in sky[key]]
        x = box["x"] + box["w"] - row_width(parts) if box["align"] == "right" else box["x"]
        place_text(m, parts, x, box["y"])
        m.alpha_composite(s["horizon"][key], tuple(box["icon"]))


def mockup(bg, s, clock=("1", "52", "pm"), sky=None):
    m = bg.copy()
    if sky:
        draw_sky(m, s, sky)
    # The block is centred for a two-digit hour; the hour is right-aligned
    # against the colon so the colon and minutes never move.
    b = s["big"]
    ampm = s[clock[2]]
    digit_w, colon_w, gap = b["0"].width, b[":"].width, 2 * P
    t = LAYOUT["time"]
    t["hour_x"] = int(CENTER - (4 * digit_w + colon_w + gap + s["pm"].width) / 2)
    t["colon_x"] = t["hour_x"] + 2 * digit_w
    t["minute_x"] = t["colon_x"] + colon_w
    t["ampm_x"] = t["minute_x"] + 2 * digit_w + gap
    t["ampm_y"] = t["y"] + BIG_BASELINE - SMALL_BASELINE
    place_text(m, [b[d] for d in clock[0]], t["colon_x"] - digit_w * len(clock[0]), t["y"])
    place_text(m, [b[":"]] + [b[d] for d in clock[1]], t["colon_x"], t["y"])
    m.alpha_composite(ampm, (t["ampm_x"], t["ampm_y"]))

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


def sky_at(minute, rise, sunset, next_rise, phase):
    """Where the sun or moon is at a minute of the day; the face's drawSky()
    works it out the same way."""
    if rise <= minute < sunset:
        return {"body": "sun", "a": 180 * (minute - rise) / (sunset - rise)}
    start, end = (sunset, next_rise + 1440) if minute >= sunset else (sunset - 1440, rise)
    return {"body": "moon", "a": 180 * (minute - start) / (end - start), "phase": phase}


def hm12(minute):
    h, mm = divmod(minute, 60)
    return f"{(h % 12) or 12}:{mm:02d}"


# Mockup day: sunrise 7:02, sunset 5:41 pm, a last-quarter moon.
MOCK_SUN = (422, 1061, 423)
MOCK_PHASE = 6


def mock_sky(minute):
    sky = sky_at(minute, *MOCK_SUN, MOCK_PHASE)
    sky.update(rise=hm12(MOCK_SUN[0]), set=hm12(MOCK_SUN[1]))
    return sky


def on_screen(m):
    screen = Image.new("L", m.size, 0)
    sp = screen.load()
    for y in range(SIZE):
        for x in range(SIZE):
            if math.hypot(x + 0.5 - CENTER, y + 0.5 - CENTER) <= CENTER:
                sp[x, y] = 255
    return Image.composite(m, Image.new("RGBA", m.size, BLACK), screen)


def clock_of(minute):
    h, mm = divmod(minute, 60)
    return str((h % 12) or 12), f"{mm:02d}", "am" if h < 12 else "pm"


def main():
    check_fit()
    s = build_sprites()
    bg = build_background(s)
    build_sky(s)
    shown = on_screen(mockup(bg, s, sky=mock_sky(13 * 60 + 52)))
    shown.convert("RGB").save(ROOT / "art" / "mockup.png")
    save(shown.resize((PREVIEW, PREVIEW), Image.LANCZOS), "preview.png")
    # Morning, behind the HP orb, behind the compass, evening, behind the plaque, before dawn.
    times = [8 * 60 + 30, 9 * 60 + 42, 12 * 60 + 21, 19 * 60 + 10, 21, 5 * 60 + 40]
    sheet = Image.new("RGB", (SIZE * 3, SIZE * 2), (40, 40, 40))
    for i, minute in enumerate(times):
        frame = on_screen(mockup(bg, s, clock=clock_of(minute), sky=mock_sky(minute)))
        sheet.paste(frame.convert("RGB"), ((i % 3) * SIZE, (i // 3) * SIZE))
    sheet.save(ROOT / "art" / "sky_states.png")
    write_layout()


PREVIEW = 314  # the Active 2's watch face preview size


def write_layout():
    consts = {"SIZE": SIZE, "CENTER": CENTER, "FILL_STEPS": FILL_STEPS, "COMPASS_STEPS": COMPASS_STEPS,
              "MOON_PHASES": MOON_PHASES}
    lines = ["// Generated by art/make_art.py; edit that, not this.", ""]
    lines += [f"export const {k} = {json.dumps(v)}" for k, v in consts.items()]
    lines += [f"export const LAYOUT = {json.dumps(LAYOUT, indent=2)}", "",
              f"export const SIZES = {json.dumps(SIZES, indent=2, sort_keys=True)}", ""]
    (ROOT / "watchface" / "layout.js").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()

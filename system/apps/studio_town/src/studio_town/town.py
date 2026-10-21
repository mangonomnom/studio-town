"""Draws the town: one building per app, along a winding path, in the storyboard's style."""

import hashlib
import html
import math

from studio_town.drawing import (
    BUTTER,
    BUTTER_D,
    CLAY,
    EUC,
    EUC_D,
    EUC_L,
    HAZE,
    HAZE_L,
    INK,
    INK_L,
    PEONY,
    PEONY_D,
    PEONY_L,
    YOU,
    Scene,
    avatar,
    circle,
    house,
    path,
    rect,
    sparkle,
    star4,
    t,
    wpath,
)

WIDTH = 400
TOP = 170
STEP = 118

# Known apps get a building that suits them; anything else gets a cottage in its own colour.
KINDS = {
    "foodie-map": ("diner", "foodie map"),
    "expense-tracker": ("bank", "expenses"),
    "health-diary": ("greenhouse", "health diary"),
    "octopus": ("newsstand", "daily briefing"),
}

COTTAGE_COLOURS = [(PEONY_L, CLAY), (HAZE_L, HAZE), ("#E4EADF", EUC_D), ("#F4EACB", BUTTER_D), ("#EFE3F0", "#A58FAE")]


def kind_and_label(app_name: str, display_name: str) -> tuple[str, str]:
    if app_name in KINDS:
        return KINDS[app_name]
    label = display_name if display_name and display_name != app_name else app_name.replace("-", " ")
    return "cottage", label


def _cottage_colour(app_name: str) -> tuple[str, str]:
    h = int(hashlib.sha1(app_name.encode()).hexdigest(), 16)
    return COTTAGE_COLOURS[h % len(COTTAGE_COLOURS)]


# ---------------------------------------------------------------- building kits
# Each kit draws at (cx, by): the building's bottom centre. Returns (wash, ink, height).


def diner(cx, by):
    ink = rect(cx - 48, by - 58, 96, 58, 3, fill=PEONY_L)
    ink += rect(cx - 10, by - 34, 20, 34, 3, fill=BUTTER, sw_=1.5)
    ink += rect(cx - 40, by - 46, 22, 18, 2, fill=BUTTER, sw_=1.4) + rect(cx + 18, by - 46, 22, 18, 2, fill=BUTTER, sw_=1.4)
    for i in range(6):
        ink += rect(cx - 54 + i * 18, by - 72, 18, 14, 0, fill=CLAY if i % 2 == 0 else "#FFFDF8", sw_=1.2)
    ink += path(f"M{cx-54} {by-58} " + " ".join(f"Q{cx-45+i*18} {by-50} {cx-36+i*18} {by-58}" for i in range(6)), fill="#FFFDF8", w=1.2)
    return "", ink, 72


def bank(cx, by):
    return "", house(cx - 46, by, 92, 62, HAZE_L, HAZE, window="#FFFDF8"), 100


def greenhouse(cx, by):
    ink = path(f"M{cx-50} {by} V{by-36} Q{cx} {by-86} {cx+50} {by-36} V{by} Z", fill="#EEF2E8")
    ink += path(f"M{cx-18} {by} V{by-66} M{cx+18} {by} V{by-66} M{cx-50} {by-24} H{cx+50}", w=1.1, color=INK_L)
    for lx in (cx - 34, cx, cx + 34):
        ink += path(f"M{lx} {by} V{by-10} M{lx} {by-6} Q{lx-6} {by-12} {lx-8} {by-8} M{lx} {by-8} Q{lx+6} {by-14} {lx+8} {by-10}", w=1.2, color=EUC_D)
    return "", ink, 72


def newsstand(cx, by):
    ink = rect(cx - 42, by - 56, 84, 56, 3, fill="#F4EACB")
    ink += path(f"M{cx-52} {by-54} L{cx} {by-86} L{cx+52} {by-54} Z", fill=HAZE)
    ink += rect(cx - 32, by - 46, 64, 24, 2, fill="#FFFDF8", sw_=1.4)
    for i in range(4):
        ink += rect(cx - 28 + i * 15, by - 42, 11, 16, 1, fill=[PEONY_L, HAZE_L, "#E4EADF", BUTTER][i], sw_=0.9)
    ink += rect(cx - 8, by - 18, 16, 18, 2, fill=BUTTER_D, sw_=1.2)
    return "", ink, 86


def cottage(cx, by, app_name):
    body, roof = _cottage_colour(app_name)
    return "", house(cx - 42, by, 84, 56, body, roof, window=BUTTER), 92


def lot(cx, by):
    ink = rect(cx - 40, by - 54, 80, 54, 4, color=INK_L, extra='stroke-dasharray="5 5"')
    ink += path(f"M{cx} {by-38} V{by-16} M{cx-11} {by-27} H{cx+11}", w=2.2, color=CLAY)
    ink += path(f"M{cx-48} {by} V{by-74} H{cx+30} M{cx-48} {by-62} L{cx-30} {by-74}", w=1.3, color=INK_L)
    return "", ink, 74


def vines(cx, by, w, h):
    """Lush, flowering vines over a building: a quiet place growing wild (never decay)."""
    x0, x1, y0 = cx - w / 2, cx + w / 2, by - h
    wash = circle(cx, by - h / 2, max(w, h) * 0.78, fill="#E1EAD3", w=0, extra='opacity="0.9"')
    ink = ""
    ds = [f"M{x0} {by} Q{x0-8} {by-h*0.4} {x0+8} {by-h*0.6} Q{x0-6} {by-h*0.8} {x0+10} {y0+4}",
          f"M{x1} {by} Q{x1+8} {by-h*0.35} {x1-8} {by-h*0.58} Q{x1+6} {by-h*0.82} {x1-10} {y0+4}",
          f"M{x0+6} {y0+8} Q{cx} {y0-18} {x1-6} {y0+8}"]
    for d in ds:
        ink += path(d, w=2, color=EUC_D)
    pts = [(x0 + 2, by - h * f) for f in (0.15, 0.35, 0.55, 0.75)] + [(x1 - 2, by - h * f) for f in (0.2, 0.42, 0.62, 0.85)]
    pts += [(x0 + w * f, y0 - 2 - 8 * math.sin(math.pi * f)) for f in (0.2, 0.4, 0.6, 0.8)]
    for n, (lx, ly) in enumerate(pts):
        d = f"M{lx:.1f} {ly:.1f} q7 -9 14 -2 q-7 7 -14 2 Z" if n % 2 else f"M{lx:.1f} {ly:.1f} q-7 -9 -14 -2 q7 7 14 2 Z"
        ink += path(d, fill=EUC if n % 3 else "#B7C4A5", w=1)
    for n, (lx, ly) in enumerate(pts[1::3]):
        c = [PEONY_D, BUTTER, "#FFFDF8"][n % 3]
        ink += circle(round(lx + 4, 1), round(ly - 3, 1), 4.2, fill=c, w=1.1) + circle(round(lx + 4, 1), round(ly - 3, 1), 1.2, fill=BUTTER_D, w=0)
    for fx, fy in [(x0 - 14, y0 + 6), (x1 + 16, y0 + 20), (cx + 8, y0 - 26)]:
        wash += circle(round(fx, 1), round(fy, 1), 6, fill="#F6E7B0", w=0)
        ink += circle(round(fx, 1), round(fy, 1), 1.8, fill="#E9C45A", w=0)
    return wash, ink


def tree(x, y, s=1.0):
    wash = circle(x, y - 34 * s, 22 * s, fill=EUC, w=0) + circle(x + 14 * s, y - 22 * s, 15 * s, fill=EUC_L, w=0)
    ink = path(f"M{x} {y} V{y-26*s}", w=4 * s, color="#8A7560")
    return wash, ink


# ---------------------------------------------------------------- the town


def _layers_svg(layers) -> str:
    out = []
    for layer in layers:
        if layer["wash"]:
            out.append('<g filter="url(#wash)">' + "".join(layer["wash"]) + "</g>")
        if layer["ink"]:
            out.append('<g filter="url(#rough)">' + "".join(layer["ink"]) + "</g>")
        if layer["text"]:
            out.append("<g>" + "".join(layer["text"]) + "</g>")
    return "".join(out)


def _cloud(x, y):
    return path(f"M{x} {y} Q{x+6} {y-12} {x+18} {y-6} Q{x+26} {y-16} {x+38} {y-6} Q{x+48} {y-6} {x+46} {y+4} H{x} Z",
                fill="#FFFDF8", w=1.4)


def layout(shape: str, n: int) -> dict:
    """Where everything goes. 'tall' is a phone-shaped scroll; 'wide' fills a desktop window.
    n counts every slot, the empty lot included."""
    if shape == "wide":
        width, top, cols, step = 960, 150, 4, 175
        xs = [150, 390, 630, 870]
        rows = (n + cols - 1) // cols
        slots = [(xs[i % cols], top + 120 + (i // cols) * step) for i in range(n)]
        height = top + 120 + (rows - 1) * step + 92
        spine = 510
        paths = [f"M{spine} {top-24} V{height}"]
        paths += [f"M20 {top + 120 + r * step + 62} Q{width/2} {top + 120 + r * step + 50} {width-20} {top + 120 + r * step + 62}"
                  for r in range(rows)]
        trees = []
        for r in range(rows):
            y = top + 120 + r * step - 12
            trees += [(270, y, 0.95), (750, y, 1.05)]
            trees.append((34, y + 30, 0.9))
        clouds = [(430, 50), (640, 74), (790, 40)]
        return {"width": width, "height": height, "top": top, "slots": slots, "paths": paths, "trees": trees,
                "clouds": clouds, "sun": (width - 70, 56), "me": (spine - 30, top - 8)}
    width, top, step = WIDTH, TOP, STEP
    slots = [((112 if i % 2 == 0 else 288), top + 70 + i * step) for i in range(n)]
    height = top + 70 + (n - 1) * step + 64
    d = f"M200 {top-24}"
    for x, y in slots:
        side = -1 if x < 200 else 1
        d += f" Q{200 - side * 80} {y - 50} 200 {y + 16}"
    trees = [((356 if x < 200 else 44), y - 12, 0.9 + 0.2 * (i % 2)) for i, (x, y) in enumerate(slots)]
    return {"width": width, "height": height, "top": top, "slots": slots, "paths": [d + f" L200 {height}"],
            "trees": trees, "clouds": [(40, 64), (226, 46)], "sun": (338, 54), "me": (200, top - 16)}


def draw_town(places: list[dict], shape: str = "tall") -> tuple[str, str, dict]:
    """places: dicts with app, label, kind, wild (bool). The last slot is always the empty lot.
    Returns (painted art, clickable hotspots, layout). Little me is not painted: it moves."""
    n = len(places) + 1
    lay = layout(shape, n)
    width, height, top = lay["width"], lay["height"], lay["top"]
    base = Scene(f"0 0 {width} {height}")
    base.wash(rect(0, 0, width, top, 0, fill="#FBF3E2", sw_=0))
    base.wash(wpath(f"M0 {top-20} Q{width/2} {top-44} {width} {top-18} V{height} H0 Z", EUC_L, 0.75))
    base.wash(circle(*lay["sun"], 20, fill=BUTTER, w=0))
    for d in lay["paths"]:
        base.wash(path(d, w=24, color=BUTTER, extra='opacity="0.8"'))
    base.new()
    for cx, cy in lay["clouds"]:
        base.ink(_cloud(cx, cy))
    bx = lay["clouds"][0][0] + 110 if shape == "tall" else 560
    base.ink(path(f"M{bx} 56 Q{bx+4} 52 {bx+8} 56 Q{bx+12} 52 {bx+16} 56", w=1.2, color=INK_L))
    for tx, ty, ts in lay["trees"]:
        w_, i_ = tree(tx, ty, ts)
        base.wash(w_)
        base.ink(i_)

    groups = []
    for i, (x, y) in enumerate(lay["slots"]):
        s = Scene()
        if i < len(places):
            p = places[i]
            kit = {"diner": diner, "bank": bank, "greenhouse": greenhouse, "newsstand": newsstand}.get(p["kind"])
            wash, ink, h = kit(x, y) if kit else cottage(x, y, p["app"])
            if p.get("wild"):
                vw, vi = vines(x, y, 104, h)
                s.wash(vw)
            s.wash(wash)
            s.ink(ink)
            if p.get("wild"):
                s.new()
                s.ink(vi)
            label, app = p["label"], p["app"]
        else:
            wash, ink, h = lot(x, y)
            s.ink(ink)
            label, app = "build something new", "__lot__"
        s.new()
        lw = max(78, 7.4 * len(label) + 18)
        s.ink(rect(round(x - lw / 2, 1), y + 6, round(lw, 1), 20, 4, fill="#FFFDF8", sw_=1.3))
        s.text(t(x, y + 21, html.escape(label), 13, CLAY if app == "__lot__" else INK, "middle", 700))
        hit = rect(x - 64, y - h - 20, 128, h + 52, 12, fill="transparent", sw_=0, extra='class="hit"')
        groups.append((f'<g class="place" data-app="{html.escape(app)}" tabindex="0" role="button" '
                       f'aria-label="{html.escape(label)}">{hit}</g>', s.layers))

    # Everything is drawn in just two filtered passes (all washes, then all pencil lines):
    # each filter pass is costly to paint, so one pass per building made the page slow.
    washes = [w for layer in base.layers + [l for g in groups for l in g[1]] for w in layer["wash"]]
    inks = [i for layer in base.layers + [l for g in groups for l in g[1]] for i in layer["ink"]]
    texts = [x for layer in base.layers + [l for g in groups for l in g[1]] for x in layer["text"]]
    art = (f'<svg class="town" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
           '<g filter="url(#wash)">' + "".join(washes) + "</g>"
           '<g filter="url(#rough)">' + "".join(inks) + "</g>"
           "<g>" + "".join(texts) + "</g></svg>")
    hotspots = (f'<svg class="hotspots" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
                + "".join(g[0] for g in groups) + "</svg>")
    return art, hotspots, lay

"""The town as one floating island: 3/4-view buildings around a plaza, drawn with pencil and watercolour.

draw_island(places, shape) -> (art svg, hotspots svg, layout). 'wide' fills a desktop window;
'tall' is a phone-shaped island. Each app gets a building that suits it (unknown apps get a
cottage in their own colour); the last spot is always the plot where the next app goes.
Little me is not painted here: it is a live, draggable overlay.
"""

import hashlib
import html
import math
import random

from studio_town.drawing import t

INK = "#5A4A3C"
FINE = "#8C7A66"
GRASS = "#C4D3A8"
GRASS_HI = "#D0DDB6"
GRASS_DK = "#93AA79"
TUFT = "#86A06F"
EARTH = ["#D8B894", "#C9A47F", "#B58F6C"]
STONE, STONE_SH = "#F1E9DA", "#D9CDB8"
SOIL, SOIL_DK = "#A98463", "#8B6A4E"
SKY = "#FBF3E2"
WOOD = "#6E5A45"
CLAY = "#C26D53"

COTTAGES = [("#F5E1DC", "#E3C7C0", "#C9887A", "#B7766A"), ("#E4EADF", "#CFD9C8", "#8FA07F", "#7D8E6E"),
            ("#F6ECD2", "#E6D6B0", "#C9A56A", "#B7945A"), ("#EFE3F0", "#DDCDE0", "#A58FAE", "#94809D")]


# ---------------------------------------------------------------- primitives

def P(d, fill="none", w=1.5, c=INK, extra=""):
    return (f'<path d="{d}" fill="{fill}" stroke="{c}" stroke-width="{w}" stroke-linecap="round" '
            f'stroke-linejoin="round" {extra}/>')


def F(d, fill, op=1.0):
    return f'<path d="{d}" fill="{fill}" opacity="{op}"/>'


def poly(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + " Z"


def ell(cx, cy, rx, ry, fill="none", w=1.2, c=INK, op=1.0):
    stroke = f'stroke="{c}" stroke-width="{w}"' if w else ""
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" {stroke} opacity="{op}"/>'


def catmull(pts, closed=True):
    n = len(pts)
    pp = pts + pts[:3] if closed else [pts[0]] + pts + [pts[-1]]
    d = f"M{pp[1][0]:.1f} {pp[1][1]:.1f}" if closed else f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in (range(1, n + 1) if closed else range(1, n)):
        p0, p1, p2, p3 = pp[i - 1], pp[i], pp[i + 1], pp[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d + (" Z" if closed else "")


def ring(cx, cy, rx, ry, n=20, jitter=0.035, seed=11):
    r = random.Random(seed)
    return [(cx + rx * math.cos(a) * (1 + r.uniform(-jitter, jitter)), cy + ry * math.sin(a) * (1 + r.uniform(-jitter, jitter)))
            for a in [2 * math.pi * i / n for i in range(n)]]


class Layer:
    def __init__(self):
        self.wash, self.ink, self.text = [], [], []


def _render(layers, cls, w, h):
    out = [f'<svg class="{cls}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">']
    for L in layers:
        if L.wash:
            out.append('<g filter="url(#wash)">' + "".join(L.wash) + "</g>")
        if L.ink:
            out.append('<g filter="url(#rough)">' + "".join(L.ink) + "</g>")
        if L.text:
            out.append("<g>" + "".join(L.text) + "</g>")
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- sky and island

def cloud(L, x, y, s=1.0):
    lobes = [(0, 0, 22), (24, -10, 26), (52, -2, 20), (72, 6, 14), (-18, 8, 13)]
    L.wash.append("".join(ell(x + dx * s, y + dy * s, r * s, r * s * 0.8, "#FFFDF8", 0) for dx, dy, r in lobes)
                  + ell(x + 26 * s, y + 14 * s, 50 * s, 8 * s, "#EFE4D0", 0, op=0.9))
    L.ink.append(P(f"M{x-30*s:.1f} {y+14*s:.1f} Q{x-26*s:.1f} {y-4*s:.1f} {x-8*s:.1f} {y-6*s:.1f} Q{x+6*s:.1f} {y-30*s:.1f} "
                   f"{x+30*s:.1f} {y-30*s:.1f} Q{x+50*s:.1f} {y-30*s:.1f} {x+56*s:.1f} {y-16*s:.1f} Q{x+82*s:.1f} {y-12*s:.1f} "
                   f"{x+86*s:.1f} {y+14*s:.1f}", w=1.2, c=FINE))


def island(layers, cx, cy, rx, ry, depth, seed=7):
    R = random.Random(seed)
    under, top = Layer(), Layer()
    rim = ring(cx, cy, rx, ry, seed=seed + 4)
    prof = [(cx + rx * 0.99, cy + 4), (cx + rx * 0.9, cy + ry * 0.55), (cx + rx * 0.72, cy + ry * 0.8 + depth * 0.25),
            (cx + rx * 0.5, cy + ry * 0.85 + depth * 0.55), (cx + rx * 0.28, cy + ry * 0.9 + depth * 0.62),
            (cx + rx * 0.12, cy + ry + depth * 0.95), (cx - rx * 0.05, cy + ry + depth * 0.78),
            (cx - rx * 0.2, cy + ry + depth * 0.9), (cx - rx * 0.4, cy + ry * 0.85 + depth * 0.55),
            (cx - rx * 0.62, cy + ry * 0.8 + depth * 0.32), (cx - rx * 0.85, cy + ry * 0.6), (cx - rx * 0.99, cy + 4)]
    body = catmull(prof, closed=False) + " Z"
    under.wash.append(F(body, EARTH[1]))
    under.wash.append(F(catmull([(prof[2][0] - 20, prof[2][1] + 30)] + prof[3:-3] + [(prof[-3][0] + 20, prof[-3][1] + 30)],
                                closed=False) + " Z", EARTH[2], 0.85))
    band = [(cx + rx * 0.97, cy + ry * 0.35), (cx + rx * 0.5, cy + ry * 1.02 + 16), (cx, cy + ry * 1.08 + 18),
            (cx - rx * 0.5, cy + ry * 1.02 + 16), (cx - rx * 0.97, cy + ry * 0.35)]
    under.wash.append(F(catmull([(cx + rx * 0.99, cy)] + band + [(cx - rx * 0.99, cy)], closed=False) + " Z", EARTH[0]))
    under.ink.append(P(body, w=1.6))
    under.ink.append(P(catmull(band, closed=False), w=1.0, c=FINE))
    for k in (0.35, 0.6):
        under.ink.append(P(catmull([(x, cy + ry + (y - cy - ry) * k + 20) for x, y in prof[2:-2]], closed=False), w=0.9, c=FINE))
    for _ in range(int(rx / 12)):
        x = cx + R.uniform(-rx * 0.7, rx * 0.7)
        y = cy + ry + 26 + R.uniform(0, depth * (1 - abs(x - cx) / rx) * 0.6)
        under.ink.append(P(f"M{x:.1f} {y:.1f} l-4 7 M{x+4:.1f} {y+1:.1f} l-4 7", w=0.8, c=FINE))
    for _ in range(max(4, int(rx / 45))):
        x = cx + R.uniform(-rx * 0.55, rx * 0.55)
        y = cy + ry + 30 + R.uniform(0, depth * (1 - abs(x - cx) / rx) * 0.5)
        r = R.uniform(5, 9)
        under.ink.append(P(f"M{x-r:.1f} {y:.1f} Q{x-r*0.6:.1f} {y-r*0.9:.1f} {x+r*0.3:.1f} {y-r*0.7:.1f} "
                           f"Q{x+r:.1f} {y-r*0.2:.1f} {x+r*0.7:.1f} {y+r*0.4:.1f} Z", fill=EARTH[0], w=0.9))
    for i in range(7):
        x = cx - rx * 0.55 + i * rx * 0.18 + R.uniform(-8, 8)
        y = cy + ry * 0.9 + depth * (1 - abs(x - cx) / rx) * 0.75
        ln = R.uniform(18, 34)
        under.ink.append(P(f"M{x:.1f} {y-6:.1f} q-5 {ln*0.4:.1f} 2 {ln*0.7:.1f} q6 {ln*0.3:.1f} -2 {ln:.1f}", w=1.1, c="#7E6048"))
        if i % 2 == 0:
            under.ink.append(P(f"M{x:.1f} {y+ln*0.55:.1f} q8 -6 12 2 q-8 5 -12 -2 Z", fill=GRASS_DK, w=0.9))
    layers.append(under)
    top.wash.append(F(catmull([(x, y + 14) for x, y in rim]), GRASS_DK))
    top.wash.append(F(catmull(rim), GRASS))
    top.wash.append(F(catmull(ring(cx - rx * 0.1, cy - ry * 0.12, rx * 0.72, ry * 0.62, n=14, jitter=0.08, seed=seed)), GRASS_HI, 0.8))
    top.ink.append(P(catmull(rim), w=1.7))
    fringe = []
    for i in range(int(rx / 6)):
        a = math.pi * 0.02 + math.pi * 0.96 * i / (rx / 6 - 1)
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        fringe.append(f"M{x:.1f} {y+12:.1f} l{R.uniform(-1,1):.1f} {R.uniform(5,11):.1f}")
    top.ink.append(P(" ".join(fringe), w=1.2, c=TUFT))
    top.ink.append(P(catmull([(x, y + 14) for x, y in rim if y > cy - ry * 0.1], closed=False), w=1.1, c=FINE))
    for _ in range(int(rx * ry / 550)):
        a, r = R.uniform(0, 2 * math.pi), math.sqrt(R.uniform(0.02, 0.9))
        x, y = cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)
        top.ink.append(P(f"M{x:.1f} {y:.1f} l1.5 -4 M{x+3:.1f} {y:.1f} l1 -5 M{x+6:.1f} {y:.1f} l-0.5 -3.5", w=0.9, c=TUFT))
    for _ in range(int(rx * ry / 1600)):
        a, r = R.uniform(0, 2 * math.pi), math.sqrt(R.uniform(0.05, 0.85))
        x, y = cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)
        top.ink.append(ell(x, y, 1.8, 1.5, R.choice(["#FFFDF8", "#F2D98C", "#E8B8B0"]), 0.6))
    for a in [0.15, 0.4, 2.6, 2.9, 3.4, 5.9]:
        x, y = cx + rx * 0.97 * math.cos(a), cy + ry * 0.97 * math.sin(a)
        top.ink.append(P(f"M{x-9:.1f} {y+3:.1f} Q{x-8:.1f} {y-8:.1f} {x+1:.1f} {y-8:.1f} Q{x+10:.1f} {y-6:.1f} {x+9:.1f} {y+3:.1f} Z",
                         fill=STONE_SH, w=1.1))
    layers.append(top)
    return catmull(rim) + " " + catmull([(x, y + 14) for x, y in rim]), body


# ---------------------------------------------------------------- props

def shadow(L, x, y, w, op=0.35):
    L.wash.append(F(f"M{x-w/2:.1f} {y:.1f} L{x+w/2+22:.1f} {y-4:.1f} L{x+w/2+40:.1f} {y+10:.1f} L{x-w/2+10:.1f} {y+14:.1f} Z",
                    "#7F9A67", op))


def tree(L, x, y, s=1.0, seed=1):
    r = random.Random(seed)
    shadow(L, x + 6 * s, y, 40 * s, 0.3)
    L.ink.append(P(f"M{x:.1f} {y:.1f} L{x+1:.1f} {y-26*s:.1f} M{x+1:.1f} {y-16*s:.1f} l7 -7", w=3 * s, c="#7E6048"))
    for dx, dy, rr in [(-10, -34, 16), (9, -38, 17), (0, -50, 15), (-2, -30, 13)]:
        L.wash.append(ell(x + dx * s, y + dy * s, rr * s, rr * s * 0.92, "#9DB685", 0))
    L.wash.append(ell(x - 6 * s, y - 46 * s, 9 * s, 7 * s, "#C2D4A5", 0))
    L.ink.append(P(f"M{x-24*s:.1f} {y-30*s:.1f} Q{x-28*s:.1f} {y-46*s:.1f} {x-12*s:.1f} {y-50*s:.1f} Q{x-8*s:.1f} {y-66*s:.1f} "
                   f"{x+8*s:.1f} {y-62*s:.1f} Q{x+26*s:.1f} {y-56*s:.1f} {x+24*s:.1f} {y-38*s:.1f} Q{x+26*s:.1f} {y-22*s:.1f} "
                   f"{x+8*s:.1f} {y-22*s:.1f}", w=1.3))
    for _ in range(5):
        a = r.uniform(0, 6.28)
        L.ink.append(P(f"M{x+12*s*math.cos(a):.1f} {y-40*s+10*s*math.sin(a):.1f} q3 -2 5 0", w=0.9, c="#6F8A5C"))


def bush(L, x, y, s=1.0, bloom=None):
    for dx, dy, rr in [(-9, -5, 9), (0, -9, 10), (9, -5, 8)]:
        L.wash.append(ell(x + dx * s, y + dy * s, rr * s, rr * s * 0.85, "#A3BB8A", 0))
    L.ink.append(P(f"M{x-18*s:.1f} {y-2*s:.1f} Q{x-20*s:.1f} {y-14*s:.1f} {x-6*s:.1f} {y-14*s:.1f} Q{x:.1f} {y-22*s:.1f} "
                   f"{x+8*s:.1f} {y-15*s:.1f} Q{x+19*s:.1f} {y-14*s:.1f} {x+17*s:.1f} {y-2*s:.1f}", w=1.2))
    if bloom:
        for dx, dy in [(-8, -10), (2, -15), (10, -8), (-2, -6)]:
            L.ink.append(ell(x + dx * s, y + dy * s, 2.2, 2, bloom, 0.7))


def flowers(L, x, y, n=7, seed=2):
    r = random.Random(seed)
    for _ in range(n):
        fx, fy = x + r.uniform(-14, 14), y + r.uniform(-5, 5)
        L.ink.append(P(f"M{fx:.1f} {fy:.1f} v-6", w=0.9, c=TUFT))
        L.ink.append(ell(fx, fy - 7, 2.4, 2.2, r.choice(["#E8B8B0", "#F2D98C", "#FFFDF8", "#C9B4D8"]), 0.7))


def lantern(L, x, y):
    L.ink.append(P(f"M{x} {y} V{y-34}", w=2, c=WOOD))
    L.ink.append(P(f"M{x-5} {y-34} h10 l-2 -10 h-6 Z", fill="#F6E3A6", w=1.1))
    L.ink.append(P(f"M{x-6} {y-44} h12 l-6 -5 Z", fill=WOOD, w=1))
    L.wash.append(ell(x, y - 39, 12, 12, "#F8E7B0", 0, op=0.5))


def bench(L, x, y):
    L.ink.append(P(f"M{x} {y} l28 -6 l0 -4 l-28 6 Z", fill="#C8A27C", w=1.0))
    L.ink.append(P(f"M{x} {y-9} l28 -6 l0 -5 l-28 6 Z", fill="#C8A27C", w=1.0))
    L.ink.append(P(f"M{x+3} {y} v6 M{x+25} {y-5} v6", w=1.4, c=WOOD))


def banner(L, x, y, text):
    """A painted board hung on the building's front: y is the top of the board."""
    w = max(60, 6.4 * len(text) + 14)
    L.ink.append(P(f"M{x-w/2+8:.1f} {y-7:.1f} v7 M{x+w/2-8:.1f} {y-7:.1f} v7", w=1.0, c=WOOD))
    L.ink.append(P(f"M{x-w/2:.1f} {y} h{w:.1f} v17 h-{w:.1f} Z", fill="#E7D2B0", w=1.2))
    L.ink.append(P(f"M{x-w/2+3:.1f} {y+3} h{w-6:.1f}", w=0.6, c="#B99772"))
    L.text.append(t(x, y + 13, html.escape(text), 11.5, INK, "middle", 700))


def sign(L, x, y, text, colour=INK):
    w = max(64, 6.6 * len(text) + 16)
    L.ink.append(P(f"M{x} {y} V{y-22}", w=2.2, c=WOOD))
    L.ink.append(P(f"M{x-w/2:.1f} {y-38} h{w:.1f} v17 h-{w:.1f} Z", fill="#E7D2B0", w=1.2))
    L.ink.append(P(f"M{x-w/2+3:.1f} {y-35} h{w-6:.1f}", w=0.6, c="#B99772"))
    L.text.append(t(x, y - 25, html.escape(text), 12, colour, "middle", 700))
    return w


def stones(L, a, ctrl, b, seed=3, every=19):
    r = random.Random(seed)
    (x0, y0), (x1, y1), (x2, y2) = a, ctrl, b
    n = max(2, int((math.hypot(x1 - x0, y1 - y0) + math.hypot(x2 - x1, y2 - y1)) // every))
    for k in range(1, n):
        f = k / n
        x = (1 - f) ** 2 * x0 + 2 * (1 - f) * f * x1 + f ** 2 * x2 + r.uniform(-2, 2)
        y = (1 - f) ** 2 * y0 + 2 * (1 - f) * f * y1 + f ** 2 * y2 + r.uniform(-1, 1)
        rx, ry = r.uniform(6.5, 8.5), r.uniform(3.2, 4.2)
        L.wash.append(ell(x + 1, y + 1.5, rx, ry, STONE_SH, 0))
        L.ink.append(ell(x, y, rx, ry, STONE, 1.0, INK))


# ---------------------------------------------------------------- buildings in 3/4 view
# Each draws at (x, y) = bottom centre of the front face and returns its bounding box
# (left, top, right, bottom) so vines, signs and hotspots can find it.

def box(L, x, y, w, h, d, front, side):
    fx0, fx1 = x - w / 2, x + w / 2
    L.wash.append(F(poly([(fx0, y), (fx1, y), (fx1, y - h), (fx0, y - h)]), front))
    L.wash.append(F(poly([(fx1, y), (fx1 + d, y - d * 0.5), (fx1 + d, y - h - d * 0.5), (fx1, y - h)]), side))
    L.ink.append(P(poly([(fx0, y), (fx1, y), (fx1, y - h), (fx0, y - h)]), w=1.5))
    L.ink.append(P(f"M{fx1} {y} L{fx1+d} {y-d*0.5} V{y-h-d*0.5} L{fx1} {y-h}", w=1.5))


def gable(L, x, y, w, h, d, roof, roof_side, over=6):
    fx0, fx1 = x - w / 2, x + w / 2
    top = y - h
    ax, ay = x, top - w * 0.42
    L.wash.append(F(poly([(fx0 - over, top + 2), (ax, ay), (fx1 + over, top + 2)]), roof))
    L.wash.append(F(poly([(ax, ay), (fx1 + over, top + 2), (fx1 + over + d, top + 2 - d * 0.5), (ax + d, ay - d * 0.5)]), roof_side))
    L.ink.append(P(poly([(fx0 - over, top + 2), (ax, ay), (fx1 + over, top + 2)]), w=1.5))
    L.ink.append(P(f"M{ax} {ay} L{ax+d} {ay-d*0.5} L{fx1+over+d} {top+2-d*0.5} L{fx1+over} {top+2}", w=1.5))
    for k in range(1, 5):
        f = k / 5
        px, py = ax + (fx1 + over - ax) * f, ay + (top + 2 - ay) * f
        L.ink.append(P(f"M{px:.1f} {py:.1f} l{d:.1f} {-d*0.5:.1f}", w=0.8, c=FINE))
    return ay - d * 0.5


def window(L, x, y, w, h, glass="#FFF6DD", shutters=None):
    L.ink.append(P(poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)]), fill=glass, w=1.2))
    L.ink.append(P(f"M{x+w/2} {y} V{y+h} M{x} {y+h/2} H{x+w}", w=0.8, c=FINE))
    L.ink.append(P(f"M{x-2} {y+h+1} h{w+4}", w=1.6))
    if shutters:
        L.ink.append(P(poly([(x - 6, y), (x - 1, y), (x - 1, y + h), (x - 6, y + h)]), fill=shutters, w=0.9))
        L.ink.append(P(poly([(x + w + 1, y), (x + w + 6, y), (x + w + 6, y + h), (x + w + 1, y + h)]), fill=shutters, w=0.9))


def door(L, x, y, w, h, colour):
    L.ink.append(P(f"M{x} {y} V{y-h+w/2} A{w/2} {w/2} 0 0 1 {x+w} {y-h+w/2} V{y} Z", fill=colour, w=1.3))
    L.ink.append(ell(x + w - 4, y - h / 2, 1.3, 1.3, INK, 0))
    L.ink.append(P(f"M{x-4} {y+1} h{w+8} v3 h-{w+8} Z", fill=STONE_SH, w=1))


def bank(L, x, y):
    shadow(L, x, y, 96)
    box(L, x, y, 84, 56, 34, "#CBD7E1", "#AFBFCC")
    top = gable(L, x, y, 84, 56, 34, "#8FA1B2", "#7C8FA2")
    L.ink.append(P(f"M{x+22} {y-86} v-16 h9 v12", fill="#B6A58F", w=1.2))
    window(L, x - 34, y - 44, 16, 16, shutters="#E8C5C0")
    window(L, x + 18, y - 44, 16, 16, shutters="#E8C5C0")
    door(L, x - 8, y, 16, 30, "#EAD7A4")
    L.ink.append(ell(x, y - 70, 7, 7, "#F6E7B8", 1.1))
    return (x - 48, top, x + 80, y), y - 62


def diner(L, x, y):
    shadow(L, x, y, 104)
    box(L, x, y, 96, 52, 32, "#F5E1DC", "#E3C7C0")
    L.wash.append(F(poly([(x - 50, y - 52), (x + 48, y - 52), (x + 80, y - 68), (x - 18, y - 68)]), "#EFE4D6"))
    L.ink.append(P(poly([(x - 50, y - 52), (x + 48, y - 52), (x + 80, y - 68), (x - 18, y - 68)]), w=1.3))
    for i in range(6):
        x0 = x - 52 + i * 17.3
        L.ink.append(P(poly([(x0, y - 50), (x0 + 17.3, y - 50), (x0 + 19, y - 36), (x0 + 1.7, y - 36)]),
                       fill=CLAY if i % 2 == 0 else "#FFF8EE", w=0.9))
    L.ink.append(P(f"M{x-50} {y-36} " + " ".join("q8.7 7 17.3 0" for _ in range(6)), fill="#FFF8EE", w=1.0))
    L.ink.append(P(poly([(x - 42, y - 28), (x + 8, y - 28), (x + 8, y - 6), (x - 42, y - 6)]), fill="#FFF6DD", w=1.2))
    L.ink.append(P(f"M{x-34} {y-10} h10 M{x-29} {y-10} v-6 M{x-16} {y-10} h10 M{x-11} {y-10} v-6", w=1, c=FINE))
    door(L, x + 16, y, 16, 30, "#EAD7A4")
    return (x - 54, y - 92, x + 82, y), y - 90


def kiosk(L, x, y):
    shadow(L, x, y, 84)
    box(L, x, y, 70, 50, 28, "#F6ECD2", "#E6D6B0")
    top = gable(L, x, y, 70, 50, 28, "#9FB0C0", "#8698AA", over=8)
    L.ink.append(P(poly([(x - 28, y - 40), (x + 28, y - 40), (x + 28, y - 22), (x - 28, y - 22)]), fill="#FFF8EE", w=1.2))
    for i, c in enumerate(["#E8C5C0", "#C3CFDA", "#D3DEC4", "#EAD7A4", "#E8C5C0"]):
        L.ink.append(P(poly([(x - 25 + i * 10.5, y - 37), (x - 17 + i * 10.5, y - 37), (x - 17 + i * 10.5, y - 25),
                             (x - 25 + i * 10.5, y - 25)]), fill=c, w=0.8))
    L.ink.append(P(f"M{x-35} {y-22} h70 l4 6 h-78 Z", fill="#C9A47F", w=1.1))
    L.ink.append(P(f"M{x-10} {y} v-14 h20 v14", fill="#EAD7A4", w=1.1))
    L.ink.append(P(f"M{x+44} {y+4} l14 -6 v-16 l-14 6 Z", fill="#FFFDF8", w=1))
    L.ink.append(P(f"M{x+47} {y-3} l8 -3 M{x+47} {y-7} l8 -3", w=0.7, c=FINE))
    return (x - 43, top, x + 63, y), y - 58


def greenhouse(L, x, y):
    shadow(L, x, y, 104)
    w, h, d = 92, 34, 34
    fx0, fx1 = x - w / 2, x + w / 2
    L.wash.append(F(f"M{fx0} {y} V{y-h} Q{x} {y-h-44} {fx1} {y-h} V{y} Z", "#EDF3EA"))
    L.wash.append(F(f"M{fx1} {y} L{fx1+d} {y-d*0.5} V{y-h-d*0.5} Q{x+d} {y-h-44-d*0.5} {x+d*0.2} {y-h-44} "
                    f"Q{x+30} {y-h-34} {fx1} {y-h} Z", "#DDE8D8"))
    L.ink.append(P(f"M{fx0} {y} V{y-h} Q{x} {y-h-44} {fx1} {y-h} V{y} Z", w=1.5))
    L.ink.append(P(f"M{fx1} {y} L{fx1+d} {y-d*0.5} V{y-h-d*0.5} Q{x+d} {y-h-44-d*0.5} {x+d*0.1} {y-h-44}", w=1.5))
    for k in (-1, 0, 1):
        L.ink.append(P(f"M{x+k*24} {y} V{y-h-(22 if k else 30)}", w=0.9, c=FINE))
    L.ink.append(P(f"M{fx0} {y-h*0.45} H{fx1} L{fx1+d} {y-h*0.45-d*0.5}", w=0.9, c=FINE))
    for px in (x - 32, x - 10, x + 14, x + 34):
        L.ink.append(P(f"M{px} {y-2} v-9 M{px} {y-7} q-5 -5 -7 -1 M{px} {y-9} q5 -6 7 -2", w=1.1, c="#6F8A5C"))
    for px in (fx0 - 8, fx1 + 42):
        L.ink.append(P(f"M{px-5} {y+2} h10 l-2 8 h-6 Z", fill="#D9906F", w=1))
        L.ink.append(P(f"M{px} {y+1} q-4 -8 -8 -8 M{px} {y+1} q4 -9 9 -7", w=1, c="#6F8A5C"))
    return (fx0 - 14, y - h - 58, fx1 + d + 12, y), y - 30


def cottage(L, x, y, app):
    front, side, roof, roof_side = COTTAGES[int(hashlib.sha1(app.encode()).hexdigest(), 16) % len(COTTAGES)]
    shadow(L, x, y, 88)
    box(L, x, y, 74, 50, 30, front, side)
    top = gable(L, x, y, 74, 50, 30, roof, roof_side)
    window(L, x - 28, y - 38, 14, 14)
    window(L, x + 14, y - 38, 14, 14)
    door(L, x - 7, y, 14, 26, "#EAD7A4")
    flowers(L, x + 50, y + 4, 4, len(app))
    return (x - 43, top, x + 67, y), y - 58


def plot(L, x, y):
    """The empty plot where the next app goes: tilled soil, a shovel, seedlings, a hopeful sign."""
    pts = [(x - 58, y + 6), (x + 38, y + 6), (x + 70, y - 12), (x - 26, y - 12)]
    L.wash.append(F(poly(pts), SOIL))
    L.ink.append(P(poly(pts), w=1.4))
    for k in range(1, 5):
        f = k / 5
        L.ink.append(P(f"M{x-58+32*f:.1f} {y+6-18*f:.1f} L{x+38+32*f:.1f} {y+6-18*f:.1f}", w=1.0, c=SOIL_DK))
    for px in (x - 34, x - 6, x + 22):
        L.ink.append(P(f"M{px} {y-2} v-6 M{px} {y-6} q-4 -4 -6 0 M{px} {y-7} q4 -5 6 -1", w=1.1, c="#6F8A5C"))
    # a shovel stuck in the soil
    L.ink.append(P(f"M{x+48} {y-4} L{x+62} {y-52}", w=2.6, c="#9C7A5B"))
    L.ink.append(P(f"M{x+58} {y-52} h9 v-5 h-9 Z", fill="#9C7A5B", w=1))
    L.ink.append(P(f"M{x+44} {y+8} Q{x+40} {y-8} {x+48} {y-10} L{x+54} {y-8} Q{x+60} {y+4} {x+52} {y+10} Z", fill="#C9CFD3", w=1.2))
    # a small mound of dug earth and a seed packet
    L.ink.append(P(f"M{x-72} {y+10} Q{x-64} {y-4} {x-52} {y+8} Z", fill=SOIL_DK, w=1))
    L.ink.append(P(poly([(x - 4, y - 16), (x + 10, y - 20), (x + 12, y - 8), (x - 2, y - 4)]), fill="#F2D98C", w=1))
    return (x - 76, y - 60, x + 72, y + 12)


KITS = {"diner": diner, "bank": bank, "greenhouse": greenhouse, "newsstand": kiosk}


# Front face of each building kind for the vines to climb: (wall width, wall height, roof rise, side depth).
FACES = {"diner": (96, 52, 16, 32), "bank": (84, 56, 35, 34), "newsstand": (70, 50, 29, 28),
         "greenhouse": (92, 34, 44, 34), "cottage": (74, 50, 31, 30)}
VINE, LEAF, LEAF_PALE = "#6F8A5C", "#9DB685", "#B7C4A5"
BLOOMS = ["#E8B8B0", "#F2D98C", "#FFFDF8"]


def _strand(pts):
    """A vine through (start, control, end, control, end, ...) as quadratic curves, plus points along it."""
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}" + "".join(
        f" Q{pts[i][0]:.1f} {pts[i][1]:.1f} {pts[i+1][0]:.1f} {pts[i+1][1]:.1f}" for i in range(1, len(pts) - 1, 2))
    along = []
    for i in range(0, len(pts) - 2, 2):
        (x0, y0), (cx, cy), (x1, y1) = pts[i], pts[i + 1], pts[i + 2]
        for k in range(4):
            f = (k + 0.5) / 4
            along.append(((1 - f) ** 2 * x0 + 2 * (1 - f) * f * cx + f ** 2 * x1,
                          (1 - f) ** 2 * y0 + 2 * (1 - f) * f * cy + f ** 2 * y1))
    return d, along


def vines(L, box_, x, y, kind="cottage", seed=1):
    """Lush, flowering vines over a building that has been quiet: a little mystery, never decay.

    Drawn as in the storyboard's "Quiet places grow wild": strands climb the front corners from
    the ground, arch over the roof, curl up from the doorstep, with leaves and blooms along them.
    """
    x0, y0, x1, y1 = box_
    w, h, rise, d = FACES.get(kind, FACES["cottage"])
    fx0, fx1, wt, apex = x - w / 2, x + w / 2, y - h, y - h - rise
    r = random.Random(seed)
    strands = [
        [(fx0 + 5, y), (fx0 - 6, y - h * 0.45), (fx0 + 6, y - h * 0.68), (fx0 - 4, y - h * 0.88), (fx0 + 4, wt - 2)],
        [(fx1 - 5, y), (fx1 + 6, y - h * 0.42), (fx1 - 6, y - h * 0.66), (fx1 + 4, y - h * 0.9), (fx1 - 3, wt - 2)],
        [(fx0 - 2, wt + 2), (x - w * 0.26, apex + rise * 0.1), (x, apex + 5), (x + w * 0.26, apex + rise * 0.1), (fx1 + 3, wt + 2)],
        [(fx1 + d - 3, y - d * 0.5), (fx1 + d + 5, y - d * 0.5 - h * 0.5), (fx1 + d - 2, y - d * 0.5 - h * 0.85)],
        [(x - w * 0.3, y), (x - w * 0.36, y - h * 0.22), (x - w * 0.26, y - h * 0.34)],
        [(x + w * 0.24, y), (x + w * 0.32, y - h * 0.2), (x + w * 0.2, y - h * 0.3)],
    ]
    spots = []
    for pts in strands:
        path, along = _strand(pts)
        L.ink.append(P(path, w=1.9, c=VINE))
        spots += along
    for n, (lx, ly) in enumerate(spots):
        lx, ly = lx + r.uniform(-1.5, 1.5), ly + r.uniform(-1.5, 1.5)
        leaf = f"M{lx:.1f} {ly:.1f} q6 -8 12 -2 q-6 6 -12 2 Z" if n % 2 else f"M{lx:.1f} {ly:.1f} q-6 -8 -12 -2 q6 6 12 2 Z"
        L.ink.append(P(leaf, fill=LEAF if n % 3 else LEAF_PALE, w=0.9))
    for n, (bx, by) in enumerate(spots[1::3]):
        L.ink.append(ell(bx + r.uniform(-3, 3), by - 3, 3.6, 3.4, BLOOMS[n % 3], 1.0))
        L.ink.append(ell(bx, by - 3, 1.1, 1.1, "#D9A94A", 0))
    for fx, fy in [(x0 - 10, y0 + 12), (x1 + 6, y0 + 20), (x, apex - 16), (x0 - 4, y1 - 20), (x1 + 2, y1 - 30)]:
        L.wash.append(ell(fx, fy, 6, 6, "#F6E7B0", 0))
        L.ink.append(ell(fx, fy, 1.8, 1.8, "#E9C45A", 0))


# ---------------------------------------------------------------- layout

WIDE_ANGLES = [-150, -90, -28, 48, 165, -120, -58, 12, 138, -172]
PLOT_ANGLE = 108


def layout(shape: str, n_apps: int) -> dict:
    """Island size and where each building and the plot stand (bottom-centre of the front face)."""
    if shape == "wide":
        extra = max(0, n_apps - 6)
        rx, ry = 400 + 18 * extra, 165 + 8 * extra
        width = max(960, int(2 * rx + 160))
        cx, cy, depth = width / 2, 120 + ry, 150
        spots = []
        for i in range(n_apps):
            a = math.radians(WIDE_ANGLES[i % len(WIDE_ANGLES)])
            k = 0.62 if i < len(WIDE_ANGLES) else 0.35
            spots.append((cx + rx * k * math.cos(a), cy + ry * 0.58 * k / 0.62 * math.sin(a) + 30))
        a = math.radians(PLOT_ANGLE)
        plot_at = (cx + rx * 0.62 * math.cos(a) - 10, cy + ry * 0.58 * math.sin(a) + 38)
        plaza = (cx - 10, cy + 48)
        height = int(cy + ry + depth + 40)
        clouds = [(width * 0.4, 58, 0.8), (width * 0.7, 40, 0.6), (width * 0.86, 140, 0.55)]
    else:
        width, rx = 400, 188
        rows = n_apps + 1
        ry = 84 + 58 * rows
        cx, cy, depth = 200, 150 + ry, 110
        top = cy - ry
        spots = [((122 if i % 2 == 0 else 262), top + 178 + 116 * i) for i in range(rows)]
        plot_at = spots.pop()
        plaza = (200, top + 62)
        height = int(cy + ry + depth + 30)
        clouds = [(52, 64, 0.6), (250, 40, 0.5)]
    return {"shape": shape, "width": int(width), "height": height, "cx": cx, "cy": cy, "rx": rx, "ry": ry, "depth": depth,
            "spots": spots, "plot": plot_at, "plaza": plaza, "me": (plaza[0], plaza[1] + 12), "clouds": clouds,
            "sun": (int(width) - 70, 150 if shape == "wide" else 128)}


def _free(pt, boxes, pad=18):
    x, y = pt
    return all(not (b[0] - pad < x < b[2] + pad and b[1] - pad < y < b[3] + pad + 30) for b in boxes)


NIGHT_SKY = "#2F3352"
NIGHT_TINT = "#3A3560"
# a watercolour night, top to horizon: ink, slate blue, lavender, lilac, peony, a warm glow
NIGHT_BANDS = ["#2F3352", "#4C5784", "#7F75AE", "#B793C4", "#E6B8C8", "#F6DCC9", "#FAEBCF"]
GLOW = "#F6D98A"


def moon(L, x, y, r=20):
    L.wash.append(ell(x, y, r * 1.7, r * 1.7, "#F3E6B8", 0, op=0.08))
    d = f"M{x:.1f} {y-r:.1f} A{r} {r} 0 1 0 {x+r*0.8:.1f} {y+r*0.6:.1f} A{r*0.78:.1f} {r*0.78:.1f} 0 1 1 {x:.1f} {y-r:.1f} Z"
    L.ink.append(P(d, fill="#F6EBC4", w=1.4, c="#E3D4A4"))


def night_sky(L, W, H, horizon, seed=5, pad=0):
    """Layered washes that arch over the island like a painted night: inky at the top, glowing low down.
    Each band is laid twice, a pale bleed and then the body, so the edges melt like wet watercolour."""
    r = random.Random(seed)
    x0, x1 = -pad - 40, W + pad + 40
    L.wash.append(F(f"M{x0} -40 H{x1} V{H+40} H{x0} Z", NIGHT_BANDS[0]))
    n = len(NIGHT_BANDS) - 1
    for k, col in enumerate(NIGHT_BANDS[1:], start=1):
        top = H * 0.92 * (k / n) ** 1.05 - 20
        pts = []
        for i in range(10):
            x = x0 + (x1 - x0) * i / 9
            arch = -0.09 * H * math.sin(math.pi * i / 9)  # rises in the middle, like the reference
            pts.append((x, top + arch + r.uniform(-0.02, 0.02) * H))
        edge = catmull(pts, closed=False)
        body = edge + f" L{x1} {H+40} L{x0} {H+40} Z"
        bleed = catmull([(x, y - 0.035 * H) for x, y in pts], closed=False) + f" L{x1} {H+40} L{x0} {H+40} Z"
        L.wash.append(F(bleed, col, 0.45))
        L.wash.append(F(body, col, 0.88))


def stars(L, W, H, seed=3, pad=0):
    """Speckled stars, thick at the top and thinning toward the glow, with a few twinkles."""
    r = random.Random(seed)
    for _ in range(int((W + 2 * pad) * H / 2600)):
        y = H * (r.random() ** 1.7) * 0.8
        x = r.uniform(4 - pad, W + pad - 4)
        size = r.uniform(0.6, 1.9) if r.random() < 0.85 else r.uniform(2.0, 2.8)
        L.ink.append(ell(x, y, size, size * r.uniform(0.8, 1.0), "#FFFDF8", 0, op=r.uniform(0.55, 1.0)))
    for _ in range(int((W + 2 * pad) / 70)):
        x, y = r.uniform(10 - pad, W + pad - 10), r.uniform(10, H * 0.35)
        s = r.uniform(2.6, 4.2)
        L.ink.append(P(f"M{x:.1f} {y-s*1.8:.1f} Q{x:.1f} {y:.1f} {x+s*1.8:.1f} {y:.1f} Q{x:.1f} {y:.1f} {x:.1f} {y+s*1.8:.1f} "
                       f"Q{x:.1f} {y:.1f} {x-s*1.8:.1f} {y:.1f} Q{x:.1f} {y:.1f} {x:.1f} {y-s*1.8:.1f} Z", fill="#FFFBEA", w=0.8, c="#FFFBEA"))


def draw_island(places: list[dict], shape: str = "wide", night: bool = False) -> tuple[str, str, dict]:
    lay = layout(shape, len(places))
    W, H = lay["width"], lay["height"]
    pad = int(W * 0.5) if shape == "wide" else 0
    cx, cy, rx, ry = lay["cx"], lay["cy"], lay["rx"], lay["ry"]
    layers = []
    sky = Layer()
    if night:
        night_sky(sky, W, H, cy, pad=pad)
    else:
        sky.wash.append(F(f"M{-pad-30} -30 H{W+pad+30} V{H+30} H{-pad-30} Z", SKY))
        sky.wash.append(ell(*lay["sun"], 24, 24, "#F2DC9E", 0))
    layers.append(sky)
    air = Layer()
    if night:
        stars(air, W, H, pad=pad)
        moon(air, *lay["sun"])
    for x, y, s in ([] if night else lay["clouds"]):
        cloud(air, x, y, s)
    if not night:
        air.ink.append(P(f"M{W*0.48:.0f} 104 q4 -4 8 0 q4 -4 8 0 M{W*0.52:.0f} 88 q3 -3 6 0 q3 -3 6 0", w=1.1, c=FINE))
    layers.append(air)
    outline = island(layers, cx, cy, rx, ry, lay["depth"])
    bits = Layer()
    for bx, by, br in [(cx - rx * 0.6, cy + ry + lay["depth"] * 0.8, 9), (cx + rx * 0.55, cy + ry + lay["depth"] * 0.85, 7)]:
        bits.ink.append(P(f"M{bx-br:.1f} {by:.1f} Q{bx-br:.1f} {by-br:.1f} {bx:.1f} {by-br:.1f} Q{bx+br:.1f} {by-br:.1f} "
                          f"{bx+br:.1f} {by:.1f} Q{bx:.1f} {by+br*1.6:.1f} {bx-br:.1f} {by:.1f} Z", fill=EARTH[1], w=1.1))
        bits.ink.append(P(f"M{bx-br:.1f} {by-2:.1f} q{br} -4 {br*2} 0", w=2, c=TUFT))
    layers.append(bits)

    # buildings first (to learn their footprints), then the ground between them
    drawn = []
    boxes = []
    for i, p in enumerate(places):
        x, y = lay["spots"][i]
        L = Layer()
        kit = KITS.get(p["kind"])
        box_, board_y = kit(L, x, y) if kit else cottage(L, x, y, p["app"])
        if p.get("wild"):
            vines(L, box_, x, y, p["kind"] if kit else "cottage", seed=i + 1)
        banner(L, x, board_y, p["label"])
        drawn.append((y, L))
        boxes.append(box_)
    px, py = lay["plot"]
    PL = Layer()
    plot_box = plot(PL, px, py)
    drawn.append((py, PL))
    boxes.append(plot_box)
    S = Layer()
    sign(S, px - 14, py + 50, "+ build something new", CLAY)
    S.ink.append(P(f"M{px+86} {py-44} v10 M{px+81} {py-39} h10", w=1.4, c=CLAY))
    S.ink.append(P(f"M{px-92} {py-30} v8 M{px-96} {py-26} h8", w=1.2, c=CLAY))
    drawn.append((py + 50, S))
    boxes.append((px - 100, py + 8, px + 70, py + 54))

    ground = Layer()
    plx, ply = lay["plaza"]
    ground.wash.append(ell(plx, ply, 58, 19, "#EFE6D3", 0))
    ground.ink.append(ell(plx, ply, 58, 19, "none", 1.0, FINE))
    targets = [(x, y + 8) for x, y in lay["spots"][:len(places)]] + [(px - 8, py + 2)]
    for k, (tx, ty) in enumerate(targets):
        mid = ((plx + tx) / 2 + (18 if tx < plx else -18), (ply + ty) / 2 + 16)
        stones(ground, (plx + (tx - plx) * 0.18, ply + (ty - ply) * 0.18), mid, (tx, ty), seed=k + 3)
    layers.append(ground)

    # scenery in the gaps: trees, bushes, flowers, a bench and a lantern by the plaza
    R = random.Random(len(places) * 7 + 1)
    props = []
    props.append((ply + 20, lambda L: lantern(L, plx + 76, ply + 18)))
    if shape == "wide":
        props.append((ply + 22, lambda L: bench(L, plx - 100, ply + 26)))
    tries, placed = 0, 0
    goal = 8 if shape == "wide" else 5
    while placed < goal and tries < 400:
        tries += 1
        a, r = R.uniform(0, 2 * math.pi), math.sqrt(R.uniform(0.15, 0.82))
        x, y = cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)
        if not _free((x, y), boxes, 26) or math.hypot(x - plx, (y - ply) * 2) < 110:
            continue
        kind = placed % 3
        seed = placed + 1
        if kind == 0:
            props.append((y, lambda L, x=x, y=y, s=seed: tree(L, x, y, 0.8 + 0.25 * R.random(), s)))
        elif kind == 1:
            props.append((y, lambda L, x=x, y=y, s=seed: bush(L, x, y, 0.9, "#E8B8B0" if s % 2 else None)))
        else:
            props.append((y, lambda L, x=x, y=y, s=seed: flowers(L, x, y, 7, s)))
        boxes.append((x - 26, y - 60, x + 26, y + 4))
        placed += 1
    for y, draw in props:
        L = Layer()
        draw(L)
        drawn.append((y, L))
    for _, L in sorted(drawn, key=lambda d: d[0]):
        layers.append(L)
    if night:
        # dusk falls over everything, then windows, the lantern and the plot's sign glow warm
        dusk = Layer()
        rim_d, body_d = outline
        dusk.text.append(f'<clipPath id="isle"><path d="{rim_d}"/><path d="{body_d}"/></clipPath>'
                         f'<rect x="-30" y="-30" width="{W+60}" height="{H+60}" fill="{NIGHT_TINT}" opacity="0.22" '
                         f'clip-path="url(#isle)"/>')
        layers.append(dusk)
        glow = Layer()
        for x0, y0, x1, y1 in boxes[:len(places)]:
            gx, gy = x0 + (x1 - x0) * 0.4, y1 - 26
            glow.wash.append(ell(gx, gy, 38, 22, GLOW, 0, op=0.35))
            glow.wash.append(ell(gx, gy, 16, 10, GLOW, 0, op=0.45))
        glow.wash.append(ell(plx + 76, ply - 21, 26, 26, GLOW, 0, op=0.5))
        layers.append(glow)

    # the sky bleeds past both sides so a wide window is filled edge to edge; the island stays centred
    art = _render(layers, "town", W, H).replace(f'viewBox="0 0 {W} {H}"', f'viewBox="{-pad} 0 {W + 2 * pad} {H}"', 1)
    lay["pad"], lay["art_width"] = pad, W + 2 * pad
    hits = []
    for i, p in enumerate(places):
        x0, y0, x1, y1 = boxes[i]
        hits.append(f'<g class="place" data-app="{html.escape(p["app"])}" tabindex="0" role="button" '
                    f'aria-label="{html.escape(p["label"])}"><rect class="hit" x="{x0-6:.0f}" y="{y0-8:.0f}" '
                    f'width="{x1-x0+12:.0f}" height="{y1-y0+60:.0f}" rx="12" fill="transparent"/></g>')
    x0, y0, x1, y1 = plot_box
    hits.append(f'<g class="place" data-app="__lot__" tabindex="0" role="button" aria-label="Build something new">'
                f'<rect class="hit" x="{x0-6:.0f}" y="{y0-8:.0f}" width="{x1-x0+12:.0f}" height="{y1-y0+60:.0f}" rx="12" '
                f'fill="transparent"/></g>')
    hotspots = (f'<svg class="hotspots" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">' + "".join(hits) + "</svg>")
    return art, hotspots, lay

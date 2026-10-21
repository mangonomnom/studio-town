"""Hand-drawn watercolour drawing kit for Studio town.

A copy of the Studio storyboard's drawing primitives (palette, pencil lines,
watercolour washes, mochi avatars, little houses), kept here so the app does
not depend on anything under the user's data folder.
"""

import math

# Palette (the user's planner palette, plus a butter and ink to round it out)
OAT = "#F7F1E6"
PAPER = "#FDFAF3"
PEONY = "#E8C5C0"
PEONY_L = "#F5E2DE"
PEONY_D = "#D4918A"
CLAY = "#C26D53"
EUC = "#A3AE9A"
EUC_L = "#CBD3C1"
EUC_D = "#7F8E78"
HAZE = "#8FA1B2"
HAZE_L = "#C3CFDA"
FOREST = "#3E5243"
BUTTER = "#EAD7A4"
BUTTER_D = "#CFB36A"
INK = "#4A4035"
INK_L = "#978B7B"


# ---------------------------------------------------------------- primitives


def t(x, y, s, size=14, color=INK, anchor="start", weight=400, font="hand", rotate=0, italic=False, extra=""):
    fam = {"hand": "Gaegu", "serif": "Fraunces", "sans": "DM Sans"}[font]
    rot = f' transform="rotate({rotate} {x} {y})"' if rotate else ""
    style = "font-style:italic;" if italic else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{color}" '
        f'text-anchor="{anchor}" font-weight="{weight}" style="{style}"{rot} {extra}>{s}</text>'
    )


def lines(x, y, rows, size=14, gap=None, **kw):
    gap = gap or size * 1.25
    return "".join(t(x, y + i * gap, r, size=size, **kw) for i, r in enumerate(rows))


def sw(w=1.8, color=INK):
    return f'stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"'


def path(d, fill="none", w=1.8, color=INK, extra=""):
    return f'<path d="{d}" fill="{fill}" {sw(w, color)} {extra}/>'


def wpath(d, fill, opacity=1.0):
    """A watercolour wash shape (no outline)."""
    return f'<path d="{d}" fill="{fill}" opacity="{opacity}"/>'


def rect(x, y, w, h, rx=8, fill="none", sw_=1.8, color=INK, extra=""):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" {sw(sw_, color)} {extra}/>'


def circle(x, y, r, fill="none", w=1.8, color=INK, extra=""):
    stroke = sw(w, color) if w else ""
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" {stroke} {extra}/>'


def sparkle(x, y, s=6, color=CLAY):
    return path(f"M{x} {y-s} V{y+s} M{x-s} {y} H{x+s} M{x-s*0.55} {y-s*0.55} L{x+s*0.55} {y+s*0.55} M{x+s*0.55} {y-s*0.55} L{x-s*0.55} {y+s*0.55}", w=1.3, color=color)


def star4(x, y, s=7, color=CLAY):
    return path(f"M{x} {y-s} Q{x} {y} {x+s} {y} Q{x} {y} {x} {y+s} Q{x} {y} {x-s} {y} Q{x} {y} {x} {y-s} Z", fill=color, w=1.1, color=color)


def arrowhead(x, y, angle_deg, s=7, color=INK):
    a = math.radians(angle_deg)
    p1 = (x - s * math.cos(a - 0.5), y - s * math.sin(a - 0.5))
    p2 = (x - s * math.cos(a + 0.5), y - s * math.sin(a + 0.5))
    return path(f"M{p1[0]:.1f} {p1[1]:.1f} L{x} {y} L{p2[0]:.1f} {p2[1]:.1f}", color=color)


def bubble(x, y, w, h, tail=None, fill="#FFFDF8", r=16, w_=1.8):
    """Rounded speech bubble. tail = ('b', tx, tipx, tipy) | ('l', ty, tipx, tipy) | ('r', ty, tipx, tipy)."""
    X2, Y2 = x + w, y + h
    top = f"M{x+r} {y} H{X2-r} Q{X2} {y} {X2} {y+r}"
    right = f" V{Y2-r}"
    bottom = f" Q{X2} {Y2} {X2-r} {Y2} H{x+r}"
    left = f" Q{x} {Y2} {x} {Y2-r} V{y+r} Q{x} {y} {x+r} {y} Z"
    if tail:
        side, at, tx, ty = tail
        if side == "b":
            bottom = f" Q{X2} {Y2} {X2-r} {Y2} H{at+9} L{tx} {ty} L{at-5} {Y2} H{x+r}"
        elif side == "l":
            left = f" Q{x} {Y2} {x} {Y2-r} V{at+8} L{tx} {ty} L{x} {at-6} V{y+r} Q{x} {y} {x+r} {y} Z"
        elif side == "r":
            right = f" V{at-6} L{tx} {ty} L{X2} {at+8} V{Y2-r}"
    return path(top + right + bottom + left, fill=fill, w=w_)


def pin(x, y, color, s=1.0):
    d = (f"M{x} {y} C{x-7*s} {y-10*s} {x-11*s} {y-15*s} {x-11*s} {y-21*s} "
         f"A{11*s} {11*s} 0 1 1 {x+11*s} {y-21*s} C{x+11*s} {y-15*s} {x+7*s} {y-10*s} {x} {y} Z")
    return path(d, fill=color, w=1.6) + circle(x, y - 21 * s, 4.2 * s, fill="#FFFDF8", w=1.3)


# ---------------------------------------------------------------- avatars

BODY = "M50 9 C74 8 91 30 92 58 C93 83 75 94 50 94 C25 94 7 84 8 58 C9 31 26 10 50 9 Z"


def _acc(kind):
    if kind == "sprout":
        return (path("M51 10 Q50 2 53 -4")
                + path("M53 -3 Q63 -14 73 -6 Q63 1 53 -3 Z", fill=EUC)
                + path("M52 0 Q44 -8 37 -3 Q44 3 52 0 Z", fill=EUC_L))
    if kind == "glasses":
        return (circle(39, 54, 9, fill="#FFFFFF", extra='fill-opacity="0.35"') + circle(61, 54, 9, fill="#FFFFFF", extra='fill-opacity="0.35"')
                + path("M48 53 Q50 51 52 53") + path("M30 52 L18 48") + path("M70 52 L82 48"))
    if kind == "beret":
        return path("M20 24 Q24 6 52 5 Q82 6 80 21 Q58 29 20 24 Z", fill=CLAY) + path("M52 5 L54 -1")
    if kind == "bun":
        return circle(50, 4, 10, fill="#8A7560") + path("M40 8 Q50 14 60 8", w=1.4)
    if kind == "headphones":
        return (path("M14 50 Q12 4 50 4 Q88 4 86 50", w=3.2) + rect(6, 44, 14, 22, 6, fill=HAZE)
                + rect(80, 44, 14, 22, 6, fill=HAZE))
    if kind == "flower":
        return "".join(circle(74 + 7 * math.cos(a), 18 + 7 * math.sin(a), 5, fill=PEONY, w=1.2)
                       for a in [i * 2 * math.pi / 5 for i in range(5)]) + circle(74, 18, 3.5, fill=BUTTER, w=1)
    if kind == "partyhat":
        return (path("M16 24 L22 -16 L44 16 Z", fill=HAZE_L) + path("M19 4 L36 12 M21 -8 L30 -2", w=1.6, color=CLAY)
                + circle(22, -19, 4.5, fill=BUTTER))
    if kind == "hardhat":
        return (path("M24 28 Q25 5 50 5 Q75 5 76 28 Z", fill="#EFC85E") + path("M16 29 H84")
                + path("M50 5 V28", w=1.6))
    if kind == "cap":
        return path("M26 24 Q28 6 52 6 Q74 7 74 22 Z", fill=HAZE) + path("M72 21 Q86 20 92 26 L72 26 Z", fill=HAZE)
    if kind == "strawhat":
        return (path("M8 26 Q50 14 92 26 Q50 34 8 26 Z", fill=BUTTER) + path("M28 22 Q30 2 50 2 Q70 2 72 22 Z", fill=BUTTER)
                + path("M29 18 Q50 24 71 18", w=2.4, color=CLAY))
    if kind == "nightcap":
        return (path("M22 26 Q30 2 58 4 Q78 6 96 30 Q70 18 78 26 Q50 32 22 26 Z", fill=HAZE_L)
                + circle(97, 32, 6, fill="#FFFDF8"))
    if kind == "bow":
        return (path("M71 19 L59 8 L60 29 Z", fill=PEONY_D) + path("M71 19 L83 8 L82 29 Z", fill=PEONY_D)
                + circle(71, 19, 3.6, fill=PEONY_D))
    return ""


def avatar(x, y, s, color, acc=None, mouth="smile", look=0, wave=False, brow=False, face=True, dashed=False, blush=True, hands_up=False):
    """A mochi-blob avatar. (x, y) is its bottom-centre; s its height-ish in px.
    Returns (wash, ink) so the fill can sit in the watercolour layer."""
    k = s / 100
    tf = f'transform="translate({x-50*k:.1f},{y-94*k:.1f}) scale({k:.3f})"'
    lw = (1.0 + 1.1 * k) / k
    wash = f'<g {tf}><path d="{BODY}" transform="translate(2.5,2)" fill="{color}"/></g>' if not dashed else ""
    ink = [f'<g {tf}>']
    ink.append(f'<ellipse cx="50" cy="96" rx="32" ry="4.5" fill="{INK}" opacity="0.13"/>')
    dash = f'stroke-dasharray="{6/k*0.5:.1f} {6/k*0.6:.1f}"' if dashed else ""
    ink.append(f'<path d="{BODY}" fill="none" stroke="{INK if not dashed else INK_L}" stroke-width="{lw:.2f}" stroke-linejoin="round" {dash}/>')
    if face:
        ex = look
        if mouth == "sleep":
            ink.append(path(f"M{34+ex} 54 Q{39+ex} 59 {44+ex} 54", w=lw) + path(f"M{56+ex} 54 Q{61+ex} 59 {66+ex} 54", w=lw))
        elif mouth == "happy":
            ink.append(path(f"M{34+ex} 56 Q{39+ex} 50 {44+ex} 56", w=lw) + path(f"M{56+ex} 56 Q{61+ex} 50 {66+ex} 56", w=lw))
        else:
            ink.append(circle(39 + ex, 54, 4.2, fill=INK, w=0) + circle(61 + ex, 54, 4.2, fill=INK, w=0))
            ink.append(circle(40.5 + ex, 52.5, 1.3, fill="#FFFFFF", w=0) + circle(62.5 + ex, 52.5, 1.3, fill="#FFFFFF", w=0))
        if blush:
            ink.append(f'<ellipse cx="{29+ex}" cy="65" rx="6.5" ry="3.6" fill="{PEONY_D}" opacity="0.55"/>')
            ink.append(f'<ellipse cx="{71+ex}" cy="65" rx="6.5" ry="3.6" fill="{PEONY_D}" opacity="0.55"/>')
        if mouth in ("smile", "happy", "sleep"):
            ink.append(path(f"M{45+ex} 64 Q{50+ex} 69.5 {55+ex} 64", w=lw))
        elif mouth == "open":
            ink.append(path(f"M{45+ex} 63 Q{50+ex} 73 {55+ex} 63 Z", fill="#9C5448", w=lw * 0.8))
        elif mouth == "o":
            ink.append(f'<ellipse cx="{50+ex}" cy="66" rx="3" ry="3.6" fill="#9C5448"/>')
        if brow:
            ink.append(path(f"M{33+ex} 42 Q{38+ex} 38 {44+ex} 41", w=lw) + path(f"M{56+ex} 44 L{66+ex} 44", w=lw))
    ink.append("".join(_acc(a) for a in (acc if isinstance(acc, list) else [acc])) if acc else "")
    if wave:
        ink.append(path("M90 62 Q104 54 105 40", w=lw) + circle(105, 36, 5.5, fill=color, w=lw))
    if hands_up:
        ink.append(f'<ellipse cx="22" cy="92" rx="10" ry="6.5" fill="{color}" stroke="{INK}" stroke-width="{lw:.2f}"/>')
        ink.append(f'<ellipse cx="78" cy="92" rx="10" ry="6.5" fill="{color}" stroke="{INK}" stroke-width="{lw:.2f}"/>')
    ink.append("</g>")
    return wash, "".join(ink)


YOU = dict(color=PEONY, acc="sprout")
JUN = dict(color=EUC, acc="glasses")
HANA = dict(color=HAZE_L, acc="bow")
MOM = dict(color=BUTTER, acc="beret")


# ---------------------------------------------------------------- scene composer


class Scene:
    """A scene is a stack of layers; each layer has a wash, an ink and a text part."""

    def __init__(self, vb="0 0 400 280"):
        self.vb = vb
        self.layers = []
        self.new()

    def new(self):
        self.layers.append({"wash": [], "ink": [], "text": []})
        return self

    def wash(self, *s):
        self.layers[-1]["wash"].extend(s)

    def ink(self, *s):
        self.layers[-1]["ink"].extend(s)

    def text(self, *s):
        self.layers[-1]["text"].extend(s)

    def av(self, *a, **kw):
        w, i = avatar(*a, **kw)
        self.wash(w)
        self.ink(i)

    def render(self, cls="scene"):
        out = [f'<svg class="{cls}" viewBox="{self.vb}" xmlns="http://www.w3.org/2000/svg" role="img">']
        for L in self.layers:
            if L["wash"]:
                out.append('<g filter="url(#wash)">' + "".join(L["wash"]) + "</g>")
            if L["ink"]:
                out.append('<g filter="url(#rough)">' + "".join(L["ink"]) + "</g>")
            if L["text"]:
                out.append("<g>" + "".join(L["text"]) + "</g>")
        out.append("</svg>")
        return "".join(out)


def cloud_path(cx, cy, rx, ry, n=11):
    pts = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        r = math.dist(a, b) * 0.62
        d += f" A{r:.1f} {r:.1f} 0 0 1 {b[0]:.1f} {b[1]:.1f}"
    return d + " Z"


def house(x, y, w, h, body, roof, door=BUTTER, window=None, sw_=1.8):
    """A little side-view house; (x, y) is the bottom-left corner."""
    out = rect(x, y - h, w, h, 3, fill=body, sw_=sw_)
    out += path(f"M{x-8} {y-h+4} L{x+w/2} {y-h-w*0.42} L{x+w+8} {y-h+4} Z", fill=roof, w=sw_)
    dw = w * 0.26
    out += rect(x + w / 2 - dw / 2, y - h * 0.5, dw, h * 0.5, 3, fill=door, sw_=sw_ * 0.8)
    if window:
        out += rect(x + w * 0.1, y - h * 0.78, w * 0.2, w * 0.2, 2, fill=window, sw_=sw_ * 0.7)
        out += rect(x + w * 0.7, y - h * 0.78, w * 0.2, w * 0.2, 2, fill=window, sw_=sw_ * 0.7)
    return out


def check(x, y, color=EUC_D):
    return path(f"M{x} {y} L{x+4} {y+4} L{x+11} {y-4}", w=2, color=color)


FILTERS = """
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <filter id="rough" x="-8%" y="-8%" width="116%" height="116%">
      <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" seed="4" result="t"/>
      <feDisplacementMap in="SourceGraphic" in2="t" scale="1.5" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="wash" x="-8%" y="-8%" width="116%" height="116%">
      <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="9" result="t"/>
      <feDisplacementMap in="SourceGraphic" in2="t" scale="9" xChannelSelector="R" yChannelSelector="G" result="d"/>
      <feGaussianBlur in="d" stdDeviation="0.5"/>
    </filter>
  </defs>
</svg>
"""

"""FundingRock talking-head reel: kinetic captions, pop-in UI cards,
"dark mode" cut-outs with a lime rim glow, gradient hero text and an end card.

Everything is drawn procedurally with Pillow/numpy in the FundingRock style
(Host Grotesk, #0E0E0E / #D9FF00 / #00D8C3) and piped to ffmpeg.

Usage: python3 reel.py INPUT.mp4 MASK.mkv OUT_silent.mp4 [--preview T1,T2,...]
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W, H, FPS = 1080, 1920, 30
SRC_END = 27.60          # last usable source frame
TOTAL = 30.0             # incl. end card

LIME = (217, 255, 0)
TEAL = (0, 216, 195)
INK = (14, 14, 14)
WHITE = (255, 255, 255)
RED = (255, 33, 86)

# ---------------------------------------------------------------- helpers


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x, s=1.9):
    x = clamp(x)
    x -= 1
    return 1 + x * x * ((s + 1) * x + s)


def ramp(t, t0, t1):
    return ease_in_out((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t0)


_fonts = {}


def font(size, weight=700):
    key = (size, weight)
    if key not in _fonts:
        f = ImageFont.truetype(os.path.join(ASSETS, "HostGrotesk.ttf"), size)
        f.set_variation_by_axes([weight])
        _fonts[key] = f
    return _fonts[key]


def text_w(s, f, tracking=0):
    if not tracking:
        return f.getlength(s)
    return sum(f.getlength(c) for c in s) + tracking * (len(s) - 1)


def draw_text(d, xy, s, f, fill, tracking=0, anchor="ls"):
    if not tracking:
        d.text(xy, s, font=f, fill=fill, anchor=anchor)
        return
    x, y = xy
    for c in s:
        d.text((x, y), c, font=f, fill=fill, anchor=anchor)
        x += f.getlength(c) + tracking


def shadow(img, radius=26, offset=(0, 18), alpha=0.65, pad=60):
    """Return img on a bigger canvas with a soft drop shadow underneath."""
    w, h = img.size
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    a = img.getchannel("A").point(lambda v: int(v * alpha))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 255))
    sh.putalpha(a)
    layer = Image.new("RGBA", out.size, (0, 0, 0, 0))
    layer.paste(sh, (pad + offset[0], pad + offset[1]), sh)
    layer = layer.filter(ImageFilter.GaussianBlur(radius))
    out.alpha_composite(layer)
    out.alpha_composite(img, (pad, pad))
    return out


def glow(img, color, radius=34, strength=0.6, pad=80):
    w, h = img.size
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    a = Image.new("L", out.size, 0)
    a.paste(img.getchannel("A"), (pad, pad))
    a = a.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(min(255, v * strength * 1.6)))
    g = Image.new("RGBA", out.size, color + (255,))
    g.putalpha(a)
    out.alpha_composite(g)
    out.alpha_composite(img, (pad, pad))
    return out


def vgrad(size, top, bot):
    w, h = size
    t = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(top, np.float32) * (1 - t) + np.array(bot, np.float32) * t
    arr = np.broadcast_to(arr, (h, w, len(top))).astype(np.uint8)
    return Image.fromarray(arr, "RGBA" if len(top) == 4 else "RGB")


def hgrad(size, left, right):
    w, h = size
    t = np.linspace(0, 1, w)[None, :, None]
    arr = np.array(left, np.float32) * (1 - t) + np.array(right, np.float32) * t
    return Image.fromarray(np.broadcast_to(arr, (h, w, 3)).astype(np.uint8), "RGB")


def rrect_mask(size, r):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255)
    return m


def panel(size, r=34, style="dark"):
    """Glassy dark (or lime) UI panel matching the reference cards."""
    w, h = size
    if style == "lime":
        body = vgrad(size, (230, 255, 60, 255), (196, 236, 0, 255))
    elif style == "white":
        body = vgrad(size, (255, 255, 255, 255), (238, 238, 238, 255))
    else:
        body = vgrad(size, (40, 40, 40, 255), (14, 14, 14, 255))
    body.putalpha(rrect_mask(size, r))
    d = ImageDraw.Draw(body)
    edge = {"lime": (255, 255, 200, 120), "white": (255, 255, 255, 255),
            "dark": (255, 255, 255, 34)}[style]
    d.rounded_rectangle((1, 1, w - 2, h - 2), r, outline=edge, width=2)
    if style == "dark":  # top sheen
        d.line((r, 2, w - r, 2), fill=(255, 255, 255, 60), width=2)
    return body


def gradient_text(s, size, weight=700, tracking=-4):
    f = font(size, weight)
    tw = int(text_w(s, f, tracking)) + 20
    asc, desc = f.getmetrics()
    m = Image.new("L", (tw, asc + desc + 10), 0)
    draw_text(ImageDraw.Draw(m), (10, asc + 4), s, f, 255, tracking)
    col = hgrad(m.size, TEAL, LIME).convert("RGBA")
    col.putalpha(m)
    return glow(col, (120, 240, 90), radius=40, strength=0.45)


def icon_check(d, cx, cy, r, bg=LIME, fg=INK, width=7):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=bg)
    d.line([(cx - r * .42, cy + r * .02), (cx - r * .1, cy + r * .33),
            (cx + r * .45, cy - r * .32)], fill=fg, width=width, joint="curve")


def icon_avatar(d, cx, cy, r, col=(150, 150, 150)):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=3)
    d.ellipse((cx - r * .35, cy - r * .55, cx + r * .35, cy + r * .15), fill=col)
    d.pieslice((cx - r * .7, cy + r * .2, cx + r * .7, cy + r * 1.2), 180, 360, fill=col)


_logo = Image.open(os.path.join(ASSETS, "logo.png")).convert("RGBA")
_mark = Image.open(os.path.join(ASSETS, "mark.png")).convert("RGBA")


def scaled(img, h):
    return img.resize((max(1, round(img.width * h / img.height)), h), Image.LANCZOS)


# ---------------------------------------------------------------- cards


def card_bubble(who, msg, light=True, brand=False):
    f1, f2 = font(22, 500), font(36, 600)
    w = int(max(text_w(msg, f2), text_w(who, f1) + 50)) + 64
    img = panel((w, 124), 30, "white" if light else "dark")
    d = ImageDraw.Draw(img)
    if brand:
        img.alpha_composite(scaled(_mark, 22), (32, 22))
    else:
        icon_avatar(d, 44, 34, 13, (140, 140, 140) if light else (170, 170, 170))
    d.text((68, 42), who, font=f1, fill=(120, 120, 120) if light else (160, 160, 160), anchor="ls")
    d.text((32, 96), msg, font=f2, fill=(17, 17, 17) if light else WHITE, anchor="ls")
    return shadow(img)


def card_program(name, style="dark", label="PROGRAM", w=430, h=160):
    img = panel((w, h), 32, style)
    d = ImageDraw.Draw(img)
    lab = (60, 60, 0) if style == "lime" else (125, 125, 125)
    txt = INK if style == "lime" else WHITE
    draw_text(d, (34, 54), label, font(20, 700), lab, tracking=2.5)
    size = 50 if len(name) < 12 else 40
    d.text((32, 118), name, font=font(size, 700), fill=txt, anchor="ls")
    out = shadow(img)
    if style == "lime":
        out = glow(out, LIME, radius=40, strength=0.55, pad=40)
    return out


def chip(s, style="lime"):
    f = font(26, 800)
    w = int(text_w(s, f, 1.5)) + 52
    img = panel((w, 58), 29, style)
    draw_text(ImageDraw.Draw(img), (26, 39), s, f, INK if style == "lime" else WHITE, 1.5)
    return glow(img, LIME, 22, 0.5, 40) if style == "lime" else shadow(img)


def card_route(progress):
    """Classic route: Phase 1 -> Phase 2 -> Funded. progress 0..1."""
    w, h = 820, 250
    img = panel((w, h), 36)
    d = ImageDraw.Draw(img)
    draw_text(d, (40, 60), "CLASSIC ROUTE", font(20, 700), (125, 125, 125), 2.5)
    d.text((40, 112), "Pass the challenge, get funded", font=font(38, 700), fill=WHITE, anchor="ls")
    xs = [100, 410, 720]
    labels = ["Phase 1", "Phase 2", "Funded"]
    y = 182
    d.line((xs[0], y, xs[2], y), fill=(60, 60, 60), width=6)
    p = clamp(progress) * (xs[2] - xs[0])
    if p > 0:
        d.line((xs[0], y, xs[0] + p, y), fill=LIME, width=6)
    for i, (x, lab) in enumerate(zip(xs, labels)):
        done = progress >= i / 2 - 1e-3
        if done:
            icon_check(d, x, y, 22, width=5)
        else:
            d.ellipse((x - 22, y - 22, x + 22, y + 22), fill=(30, 30, 30), outline=(80, 80, 80), width=3)
        d.text((x, y + 52), lab, font=font(24, 600), fill=WHITE if done else (120, 120, 120), anchor="ms")
    return shadow(img)


def card_eval(strike):
    """Evaluation checklist that gets crossed out."""
    w, h = 560, 300
    img = panel((w, h), 36)
    d = ImageDraw.Draw(img)
    draw_text(d, (40, 60), "EVALUATION", font(20, 700), (125, 125, 125), 2.5)
    for i, s in enumerate(["Phase 1", "Phase 2", "Hit the target"]):
        y = 120 + i * 62
        d.ellipse((40, y - 14, 68, y + 14), outline=(110, 110, 110), width=3)
        d.text((88, y + 12), s, font=font(32, 600), fill=(220, 220, 220), anchor="ls")
        d.line((88, y + 32, w - 50, y + 32), fill=(40, 40, 40), width=2)
    out = shadow(img)
    if strike > 0:
        ov = Image.new("RGBA", out.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        x0, y0, x1, y1 = 60 + 60, 60 + 50, 60 + w - 50, 60 + h - 30
        a = clamp(strike * 2)
        b = clamp(strike * 2 - 1)
        od.line((x0, y0, x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), fill=LIME, width=22)
        if b > 0:
            od.line((x1, y0, x1 - (x1 - x0) * b, y0 + (y1 - y0) * b), fill=LIME, width=22)
        out.alpha_composite(glow(ov, LIME, 24, 0.7, 0), (0, 0))
    return out


def card_chart(n_visible):
    """Live candlestick card (Instant: trade from day one)."""
    w, h = 470, 230
    img = panel((w, h), 32)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((28, 24, 150, 58), 17, fill=LIME)
    draw_text(d, (44, 50), "INSTANT", font(20, 800), INK, 1.5)
    d.ellipse((w - 98, 34, w - 86, 46), fill=LIME)
    draw_text(d, (w - 78, 48), "LIVE", font(18, 700), (190, 190, 190), 1.5)
    rng = np.random.default_rng(3)
    price = 150.0
    n = 16
    for i in range(min(n, int(n_visible))):
        o = price
        price = price - 5.5 + rng.normal(0, 6)
        c = price
        hi, lo = min(o, c) - rng.uniform(3, 9), max(o, c) + rng.uniform(3, 9)
        x = 44 + i * 25
        col = LIME if c < o else RED
        d.line((x, hi + 20, x, lo + 20), fill=col, width=2)
        d.rectangle((x - 6, min(o, c) + 20, x + 6, max(o, c) + 21), fill=col)
    d.text((32, h - 26), "Trading from day one", font=font(26, 600), fill=LIME, anchor="ls")
    return shadow(img)


def card_payp(progress, passed):
    """Pay After You Pass: start -> pass -> pay the rest."""
    w, h = 820, 290
    img = panel((w, h), 36)
    d = ImageDraw.Draw(img)
    draw_text(d, (40, 60), "PAY AFTER YOU PASS", font(20, 700), (125, 125, 125), 2.5)
    rows = [("Start the challenge", 0.02), ("Hit your target", 0.55), ("Pay the rest once you pass", 0.98)]
    for i, (s, at) in enumerate(rows):
        y = 118 + i * 62
        done = progress >= at
        if done:
            icon_check(d, 56, y, 17, width=4)
        else:
            d.ellipse((39, y - 17, 73, y + 17), outline=(90, 90, 90), width=3)
        d.text((92, y + 11), s, font=font(32, 600), fill=WHITE if done else (120, 120, 120), anchor="ls")
    # Progress bar on the right edge.
    bx, by, bh = w - 70, 92, 160
    d.rounded_rectangle((bx, by, bx + 14, by + bh), 7, fill=(40, 40, 40))
    fh = bh * clamp(progress)
    if fh > 2:
        d.rounded_rectangle((bx, by + bh - fh, bx + 14, by + bh), 7, fill=LIME)
    out = shadow(img)
    if passed > 0:
        st = Image.new("RGBA", (300, 96), (0, 0, 0, 0))
        sd = ImageDraw.Draw(st)
        sd.rounded_rectangle((0, 0, 299, 95), 48, fill=LIME)
        icon_check(sd, 50, 48, 28, bg=INK, fg=LIME, width=7)
        draw_text(sd, (94, 63), "PASSED", font(40, 800), INK, 2)
        st = glow(st, LIME, 30, 0.7, 50)
        k = ease_out_back(passed, 2.6)
        st = st.resize((max(1, int(st.width * k)), max(1, int(st.height * k))), Image.LANCZOS)
        st = st.rotate(-8, resample=Image.BICUBIC, expand=True)
        out.alpha_composite(st, (out.width - st.width - 10, max(0, 60 - st.height // 2 + 10)))
    return out


def end_card():
    img = Image.new("RGBA", (W, 700), (0, 0, 0, 0))
    logo = scaled(_logo, 84)
    bloom = Image.new("RGBA", (W, 700), (0, 0, 0, 0))
    ImageDraw.Draw(bloom).ellipse((W / 2 - 330, 60, W / 2 + 330, 330), fill=LIME + (40,))
    img.alpha_composite(bloom.filter(ImageFilter.GaussianBlur(90)))
    img.alpha_composite(logo, ((W - logo.width) // 2, 130))
    d = ImageDraw.Draw(img)
    f = font(40, 500)
    a, b = "Pick the route that fits ", "the way you trade."
    x = (W - text_w(a + b, f)) / 2
    d.text((x, 300), a, font=f, fill=(170, 170, 170), anchor="ls")
    d.text((x + f.getlength(a), 300), b, font=font(40, 700), fill=WHITE, anchor="ls")
    pill = Image.new("RGBA", (360, 84), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pill)
    pd.rounded_rectangle((0, 0, 359, 83), 42, fill=LIME)
    pd.text((180, 55), "fundingrock.com", font=font(36, 700), fill=INK, anchor="ms")
    pill = glow(pill, LIME, 30, 0.6, 60)
    img.alpha_composite(pill, ((W - pill.width) // 2, 340))
    return img


# ---------------------------------------------------------------- timeline

class El:
    """A graphic that pops in at t0 and out at t1 around centre (cx, cy)."""

    def __init__(self, t0, t1, cx, cy, make, rot=0.0, dyn=False, pop="back",
                 bob=4.0, delay_out=0.0):
        self.t0, self.t1, self.cx, self.cy = t0, t1, cx, cy
        self.make, self.rot, self.dyn, self.pop, self.bob = make, rot, dyn, pop, bob
        self._img = None

    def image(self, lt):
        if self.dyn:
            return self.make(lt)
        if self._img is None:
            self._img = self.make(0)
        return self._img

    def draw(self, canvas, t):
        if t < self.t0 or t > self.t1 + 0.3:
            return
        lt = t - self.t0
        a_in = clamp(lt / 0.14)
        if self.pop == "back":
            k = 0.35 + 0.65 * ease_out_back(lt / 0.38)
        elif self.pop == "slam":
            k = 1.6 - 0.6 * ease_out_cubic(lt / 0.22)
        else:
            k = 0.9 + 0.1 * ease_out_cubic(lt / 0.3)
        dy = (1 - ease_out_cubic(lt / 0.38)) * 40
        r = self.rot + (1 - ease_out_cubic(lt / 0.45)) * -7
        if t > self.t1:
            o = (t - self.t1) / 0.22
            a_in *= 1 - clamp(o)
            k *= 1 - 0.18 * ease_out_cubic(o)
            dy -= 30 * ease_out_cubic(o)
        if a_in <= 0.01:
            return
        img = self.image(lt)
        if abs(k - 1) > 1e-3:
            img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.BILINEAR)
        if abs(r) > 0.05:
            img = img.rotate(r, resample=Image.BICUBIC, expand=True)
        if a_in < 1:
            img = img.copy()
            img.putalpha(img.getchannel("A").point(lambda v: int(v * a_in)))
        bob = math.sin((t + self.cx * 0.01) * 2.1) * self.bob
        x = int(self.cx - img.width / 2)
        y = int(self.cy - img.height / 2 + dy + bob)
        canvas.alpha_composite(img, (x, y)) if 0 <= x and 0 <= y and x + img.width <= W and y + img.height <= H \
            else paste_clipped(canvas, img, x, y)


def paste_clipped(canvas, img, x, y):
    l, t = max(0, -x), max(0, -y)
    r, b = min(img.width, W - x), min(img.height, H - y)
    if r > l and b > t:
        canvas.alpha_composite(img.crop((l, t, r, b)), (x + l, y + t))


def grid_els(t0, t1, highlight=None, header="Which program?"):
    """2x2 program grid like the reference. highlight(t) -> set of names lit."""
    names = [("1-Step", 0, 0), ("2-Step", 1, 0), ("Pay After You Pass", 0, 1), ("Instant", 1, 1)]
    cache = {}

    def mk(name):
        def f(lt):
            lit = highlight(t0 + lt) if highlight else None
            st = "dark"
            if lit is not None:
                st = "lime" if name in lit else "dim"
            if st not in cache.setdefault(name, {}):
                if st == "dim":
                    im = card_program(name, "dark")
                    im.putalpha(im.getchannel("A").point(lambda v: int(v * 0.35)))
                else:
                    im = card_program(name, st)
                cache[name][st] = im
            return cache[name][st]
        return f

    els = []

    def head(_):
        f = font(34, 600)
        img = Image.new("RGBA", (int(text_w(header, f)) + 70, 60), (0, 0, 0, 0))
        img.alpha_composite(scaled(_mark, 36), (0, 10))
        ImageDraw.Draw(img).text((58, 42), header, font=f, fill=WHITE, anchor="ls")
        return img
    els.append(El(t0, t1, 540, 175, head, pop="fade", bob=0))
    for i, (n, cx, cy) in enumerate(names):
        els.append(El(t0 + 0.08 * (i + 1), t1, 312 + cx * 456, 330 + cy * 186, mk(n),
                      rot=-1.2 if cx == 0 else 1.2, dyn=True))
    return els


def hero(t0, t1, small, big, cy=330):
    els = []

    def mk_small(_):
        f = font(38, 600)
        img = Image.new("RGBA", (int(text_w(small, f)) + 20, 60), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((10, 44), small, font=f, fill=WHITE, anchor="ls")
        return img
    els.append(El(t0, t1, 540, cy - 150, mk_small, pop="fade", bob=0))
    els.append(El(t0 + 0.12, t1, 540, cy, lambda _: gradient_text(big, 230), pop="slam", bob=0))
    return els


ELS = []
# A: hook -- trader question + FundingRock reply
ELS += [El(0.10, 2.95, 400, 230, lambda _: card_bubble("Trader · now", "Which challenge do I pick?"), rot=-2),
        El(1.45, 2.95, 640, 400, lambda _: card_bubble("FundingRock Support", "How do you actually trade?",
                                                       light=False, brand=True), rot=1.5)]
# B/C: "You've got options" -> grid; "classic route" lights 1-Step + 2-Step
ELS += grid_els(4.40, 7.20, highlight=lambda t: {"1-Step", "2-Step"} if t >= 6.40 else None)
# C: classic route card + chips
ELS += [El(7.45, 10.35, 540, 430, lambda lt: card_route(clamp((lt + 7.45 - 8.25) / 1.6)), dyn=True, rot=-1),
        El(8.25, 10.35, 410, 195, lambda _: chip("1-STEP"), rot=-3, bob=6),
        El(8.95, 10.35, 670, 195, lambda _: chip("2-STEP"), rot=3, bob=6)]
# D: skip the evaluation -> 0 phases -> Instant
ELS += [El(10.62, 11.85, 540, 340, lambda lt: card_eval(clamp((lt + 10.62 - 11.15) / 0.45)), dyn=True, rot=-2)]
ELS += hero(11.95, 13.10, "evaluation phases", "0")
ELS += [El(13.27, 15.55, 265, 330, lambda _: card_program("Instant", "lime", w=340), rot=-3),
        El(13.55, 15.55, 760, 380, lambda lt: card_chart(3 + (lt) * 9), dyn=True, rot=2.5)]
# E: which route is right for you -> grid cycling highlight
cycle = ["1-Step", "2-Step", "Instant", "Pay After You Pass"]
ELS += grid_els(15.55, 17.10, header="Which route is right for you?",
                highlight=lambda t: {cycle[int(clamp((t - 15.9) / 0.3, 0, 3.99))]} if t >= 15.9 else None)
# F: Pay After You Pass
ELS += [El(17.45, 22.05, 540, 200, lambda _: chip("PAY AFTER YOU PASS"), bob=5),
        El(17.65, 22.05, 540, 420,
           lambda lt: card_payp(clamp((lt + 17.65 - 18.6) / 2.55), clamp((lt + 17.65 - 21.25) / 0.35)), dyn=True)]
# G: not every trader trades the same way
ELS += [El(22.15, 24.80, 330, 260, lambda _: card_bubble("Trader 1", "I scalp the news."), rot=-2),
        El(22.70, 24.80, 760, 420, lambda _: card_bubble("Trader 2", "I hold for weeks."), rot=2),
        El(23.60, 24.80, 560, 345, lambda _: glow(neq_badge(), LIME, 26, 0.6, 30), pop="slam", bob=0)]
# H: your way
ELS += hero(24.95, 27.15, "your trading style, your", "route.", cy=360)


def neq_badge():
    img = Image.new("RGBA", (110, 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 109, 109), fill=LIME)
    d.text((55, 80), "≠", font=font(80, 800), fill=INK, anchor="ms")
    return img


# Kinetic captions: (start, text, highlighted)
CAPS = [
    [(0.03, "Are", 0), (0.09, "you", 0), (0.32, "choosing", 0)],
    [(0.77, "the", 0), (0.88, "right", 0), (1.21, "challenge", 1)],
    [(1.59, "for", 0), (1.73, "the", 0), (1.83, "way", 0), (2.00, "you", 0)],
    [(2.15, "actually", 0), (2.48, "trade?", 1)],
    [(4.45, "You've", 0), (4.71, "got", 0), (4.87, "options.", 1)],
    [(5.63, "If", 0), (5.81, "you", 0), (5.96, "prefer", 0)],
    [(6.29, "the", 0), (6.40, "classic", 1), (6.86, "route,", 1)],
    [(7.35, "you", 0), (7.49, "can", 0), (7.67, "choose", 0), (7.91, "between", 0)],
    [(8.25, "a", 0), (8.40, "1-Step", 1)],
    [(8.80, "or", 0), (9.06, "a", 0), (9.15, "2-Step", 1)],
    [(9.70, "challenge.", 0)],
    [(10.67, "Want", 0), (10.87, "to", 0), (11.00, "skip", 0)],
    [(11.13, "the", 0), (11.30, "evaluation", 1)],
    [(11.79, "and", 0), (12.00, "go", 0), (12.15, "straight", 0)],
    [(12.52, "to", 0), (12.60, "trading?", 1)],
    [(13.27, "Instant.", 1)],
    [(15.62, "Which", 0), (15.93, "route", 1)],
    [(16.28, "is", 0), (16.40, "right", 0), (16.63, "for", 0), (16.72, "you?", 1)],
    [(17.55, "Pay", 1), (17.72, "After", 1), (17.88, "You", 1), (18.06, "Pass", 1)],
    [(20.65, "the", 0), (20.72, "rest", 0)],
    [(21.13, "once", 0), (21.42, "you", 0), (21.51, "pass.", 1)],
    [(22.12, "Because", 0), (22.43, "not", 0), (22.68, "every", 0)],
    [(22.97, "trader", 1)],
    [(23.60, "trades", 0), (24.01, "the", 0), (24.12, "same", 1), (24.47, "way.", 1)],
]
CAP_END = {15: 14.35, 18: 18.65, 3: 3.10, 4: 5.50, 10: 10.30, 14: 13.15, 17: 17.10, 20: 22.05, 23: 24.80}
CAP_Y = 1345
_word_cache = {}


def word_img(s, hl):
    key = (s, hl)
    if key not in _word_cache:
        f = font(66, 700)
        asc, desc = f.getmetrics()
        img = Image.new("RGBA", (int(f.getlength(s)) + 40, asc + desc + 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((20, 20 + asc), s, font=f, fill=LIME if hl else WHITE, anchor="ls")
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(img.getchannel("A").point(lambda v: int(v * 0.75)))
        sh = sh.filter(ImageFilter.GaussianBlur(9))
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 4))
        out.alpha_composite(img)
        _word_cache[key] = (out, f.getlength(s), asc)
    return _word_cache[key]


def draw_captions(canvas, t):
    for i, chunk in enumerate(CAPS):
        start = chunk[0][0]
        end = CAP_END.get(i, CAPS[i + 1][0][0] if i + 1 < len(CAPS) else 99)
        if not (start <= t < end):
            continue
        space = font(66, 700).getlength(" ")
        widths = [word_img(s, hl)[1] for _, s, hl in chunk]
        total = sum(widths) + space * (len(chunk) - 1)
        x = (W - total) / 2
        for (ws, s, hl), wdt in zip(chunk, widths):
            if t >= ws:
                img, _, asc = word_img(s, hl)
                lt = t - ws
                k = 0.82 + 0.18 * ease_out_back(lt / 0.2, 2.2)
                a = clamp(lt / 0.08)
                im = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR) if k != 1 else img
                if a < 1:
                    im = im.copy()
                    im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
                cx = x + wdt / 2
                canvas.alpha_composite(im, (int(cx - im.width / 2), int(CAP_Y - im.height / 2 + 10)))
            x += wdt + space


# ---------------------------------------------------------------- camera / dark mode

def dark_amount(t):
    segs = [(3.85, 4.30, 7.15, 7.45), (11.85, 12.00, 13.10, 13.30), (15.45, 15.65, 17.05, 17.35),
            (24.85, 25.10, 99, 99)]
    return max(ramp(t, a, b) * (1 - ramp(t, c, d)) for a, b, c, d in segs)


def person_scale(t):
    segs = [(4.15, 4.55, 7.10, 7.50, 0.62), (15.45, 15.80, 17.00, 17.40, 0.62), (24.85, 25.40, 99, 99, 0.80)]
    s = 1.0
    for a, b, c, d, v in segs:
        k = ramp(t, a, b) * (1 - ramp(t, c, d))
        s = s * (1 - k) + v * k if k > 0 else s
    return s


def punch(t):
    hits = [(1.21, .035), (2.48, .03), (6.40, .03), (9.15, .025), (10.67, .03), (13.27, .05),
            (17.55, .035), (21.51, .04), (22.97, .03), (24.12, .025)]
    z = 1.0 + 0.05 * clamp(t / SRC_END)
    for ti, a in hits:
        if t >= ti:
            z += a * math.exp(-(t - ti) / 0.18)
    return z


# Soft cut-out over the floor lamp (shade + pole), never where the presenter is.
_lc = Image.new("L", (540, 960), 255)
ImageDraw.Draw(_lc).rectangle((0, 0, 120, 470), fill=0)
ImageDraw.Draw(_lc).rectangle((0, 470, 62, 900), fill=0)
LAMP_CUT = np.asarray(_lc.filter(ImageFilter.GaussianBlur(6)), np.float32) / 255.0


def clean_mask(m):
    """Keep the largest blob (the presenter) -- drops the floor lamp etc."""
    m = (m.astype(np.float32) * LAMP_CUT).astype(np.uint8)
    b = m > 128
    lab, n = ndimage.label(b)
    if n > 1:
        sizes = ndimage.sum(b, lab, range(1, n + 1))
        keep = lab == (1 + int(np.argmax(sizes)))
        keep = ndimage.binary_dilation(keep, iterations=6)
        m = (m * keep).astype(np.uint8)
    return m


VIGNETTE = None


def compose_base(frame, mask, t):
    """frame: HxWx3 uint8 (1080x1920), mask: 960x540 uint8."""
    global VIGNETTE
    if VIGNETTE is None:
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx - W / 2) / (W * .62)) ** 2 + ((yy - H * .55) / (H * .6)) ** 2)
        VIGNETTE = np.clip(1.15 - 0.55 * r ** 2, 0.35, 1.0).astype(np.float32)[..., None]
    z = punch(t)
    s = person_scale(t)
    d = dark_amount(t)
    img = Image.fromarray(frame)
    m = Image.fromarray(clean_mask(mask)).resize((W, H), Image.BILINEAR)
    # Zoom around the face, then shrink toward bottom-centre for dark mode.
    scale = z * s
    cy = 760
    # affine: out(x,y) -> src((x - px)/scale + px', ...)
    a = 1 / scale
    px, py_ = (W / 2, cy) if s >= 0.999 else (W / 2, H * 0.98)
    coeffs = (a, 0, px - px * a, 0, a, py_ - py_ * a)
    img = img.transform((W, H), Image.AFFINE, coeffs, Image.BILINEAR)
    m = m.transform((W, H), Image.AFFINE, coeffs, Image.BILINEAR)
    f = np.asarray(img, np.float32) / 255.0
    ma = np.asarray(m, np.float32)[..., None] / 255.0
    f = f * VIGNETTE ** 0.5
    if d > 0:
        bg = f * (1 - 0.95 * d)
        person = f * (1 - 0.15 * d)
        out = person * ma + bg * (1 - ma)
        # Lime rim glow around the presenter.
        mb = np.asarray(m.filter(ImageFilter.GaussianBlur(22)), np.float32)[..., None] / 255.0
        rim = np.clip(mb - ma, 0, 1) * 2.2 * d
        out = out * (1 - rim * 0.5) + rim * (np.array(LIME, np.float32) / 255.0) * 0.5
    else:
        out = f
    return np.clip(out * 255, 0, 255).astype(np.uint8)


def overlay(t):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for e in ELS:
        e.draw(c, t)
    draw_captions(c, t)
    return c


END = None


def frame_at(t, src, mask):
    global END
    if src is not None:
        base = compose_base(src, mask, t)
    else:
        base = np.zeros((H, W, 3), np.uint8)
    img = Image.fromarray(base).convert("RGBA")
    img.alpha_composite(overlay(t))
    # Fade to black into the end card.
    fb = ramp(t, 27.05, 27.55)
    if fb > 0:
        black = Image.new("RGBA", (W, H), (8, 8, 8, int(255 * fb)))
        img.alpha_composite(black)
    if t >= 27.35:
        if END is None:
            END = end_card()
        lt = t - 27.35
        e = END.copy()
        a = clamp(lt / 0.35)
        e.putalpha(e.getchannel("A").point(lambda v: int(v * a)))
        k = 0.92 + 0.08 * ease_out_cubic(lt / 0.6)
        e = e.resize((int(e.width * k), int(e.height * k)), Image.BICUBIC)
        # subtle lime bloom behind the logo
        img.alpha_composite(e, ((W - e.width) // 2, int(H / 2 - e.height / 2 - 40)))
        fo = ramp(t, TOTAL - 0.35, TOTAL)
        if fo > 0:
            img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fo))))
    return np.asarray(img.convert("RGB"))


def main():
    src_path, mask_path, out = sys.argv[1:4]
    preview = None
    if len(sys.argv) > 5 and sys.argv[4] == "--preview":
        preview = [float(x) for x in sys.argv[5].split(",")]
    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", src_path, "-vf",
         f"fps={FPS},scale={W}:{H}:flags=lanczos,eq=contrast=1.05:saturation=1.06",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    mdec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", mask_path, "-f", "rawvideo",
                             "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    enc = None
    if preview is None:
        enc = subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
             "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    nfr = int(round(TOTAL * FPS))
    src = mask = None
    for i in range(nfr):
        t = i / FPS
        buf = dec.stdout.read(W * H * 3) if t < SRC_END + 0.5 else b""
        mb = mdec.stdout.read(540 * 960) if t < SRC_END + 0.5 else b""
        if len(buf) == W * H * 3 and len(mb) == 540 * 960 and t <= SRC_END:
            src = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            mask = np.frombuffer(mb, np.uint8).reshape(960, 540)
        if preview is not None:
            if any(abs(t - p) < 0.5 / FPS for p in preview):
                Image.fromarray(frame_at(t, src, mask)).save(f"{out}_{t:05.2f}.png")
            if t > max(preview):
                break
            continue
        enc.stdin.write(frame_at(t, src, mask).tobytes())
        if i % 60 == 0:
            print(f"frame {i}/{nfr}", flush=True)
    dec.kill()
    mdec.kill()
    if enc:
        enc.stdin.close()
        enc.wait()


if __name__ == "__main__":
    main()

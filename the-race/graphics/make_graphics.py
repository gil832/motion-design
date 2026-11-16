"""Render THE RACE motion graphics as ProRes 4444 (with alpha) + MP4 previews.

No AI generation: everything is drawn procedurally with Pillow and encoded
with ffmpeg. 1920x1080, 24 fps.

Usage: python3 make_graphics.py OUT_DIR [--only NAME]
"""
import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 24
LIME = (217, 255, 0)
WHITE = (255, 255, 255)
GREY = (150, 150, 150)
FONT_DIR = Path("/usr/share/fonts/opentype/inter")


def font(name, size):
    return ImageFont.truetype(str(FONT_DIR / name), size)


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(f, start, dur):
    return clamp((f - start) / dur)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


# ---------- drawing helpers ----------
def text_width(text, fnt, tracking):
    w = 0
    for i, ch in enumerate(text):
        w += fnt.getlength(ch) + (tracking if i < len(text) - 1 else 0)
    return w


def draw_tracked(img, text, fnt, cx, y, tracking, color_fn, visible_fn=None):
    """Draw text centered on cx with letter tracking; color_fn(i, ch) -> RGBA."""
    d = ImageDraw.Draw(img)
    x = cx - text_width(text, fnt, tracking) / 2
    for i, ch in enumerate(text):
        shown = ch if visible_fn is None else visible_fn(i, ch)
        if shown:
            d.text((x, y), shown, font=fnt, fill=color_fn(i, ch))
        x += fnt.getlength(ch) + tracking
    return x


def glow(layer, radius, strength=1.0):
    """Return layer composited over its own blurred copy (bloom)."""
    blurred = layer.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        a = blurred.getchannel("A").point(lambda v: min(255, int(v * strength)))
        blurred.putalpha(a)
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(blurred)
    out.alpha_composite(layer)
    return out


def with_alpha(color, a):
    return (*color[:3], int(clamp(a) * 255))


# ---------- encoder ----------
class Encoder:
    def __init__(self, path_mov, path_mp4, alpha):
        self.alpha = alpha
        self.path_mov, self.path_mp4 = path_mov, path_mp4
        self.p = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-v", "error", "-y",
             "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
             "-c:v", "prores_ks", "-profile:v", "4444",
             "-pix_fmt", "yuva444p10le" if alpha else "yuv444p10le",
             "-vendor", "apl0", path_mov],
            stdin=subprocess.PIPE)

    def write(self, img):
        self.p.stdin.write(img.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()
        # Preview MP4: alpha graphics over a dark grey so they can be judged.
        bg = "color=c=0x1a1a1a:s=1920x1080:r=24"
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-v", "error", "-y", "-f", "lavfi", "-i", bg,
             "-i", self.path_mov, "-filter_complex", "[0][1]overlay=shortest=1,format=yuv420p",
             "-c:v", "libx264", "-crf", "18", "-movflags", "+faststart", self.path_mp4],
            check=True)


# =====================================================================
# 1. End card (opaque black, 5s)
# =====================================================================
def end_card(f, rng_glyphs="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#/<>"):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    big = font("InterDisplay-Black.otf", 92)
    track = 10

    # Lines 1 + 2 lift away from frame 64.
    lift = ease_in_out(prog(f, 58, 7))
    fade_lines = 1 - lift
    y1, y2 = 400 - 40 * lift, 520 - 40 * lift

    # Line 1: hard cut on at f2, tiny scale settle faked with tracking.
    if f >= 2 and fade_lines > 0:
        settle = 1 - ease_out(prog(f, 2, 8))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_tracked(layer, "THE RACE WAS SIMULATED.", big, W / 2, y1, track + 6 * settle,
                     lambda i, c: with_alpha(WHITE, fade_lines))
        img.alpha_composite(layer)

    # Line 2: decode reveal L->R from f22 over 16 frames, lime scan line on the front.
    line2 = "THE REWARDS ARE REAL."
    real_start = line2.index("REAL.")
    if f >= 22 and fade_lines > 0:
        front = prog(f, 22, 16) * (len(line2) + 2)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        def visible(i, ch):
            if ch == " ":
                return None
            if i < front - 2:
                return ch
            if i < front:  # scrambling glyph right behind the front
                return rng_glyphs[(i * 7 + f * 13) % len(rng_glyphs)]
            return None

        def color(i, ch):
            base = LIME if i >= real_start else WHITE
            if front - 2 <= i < front:
                base = LIME
            return with_alpha(base, fade_lines)

        end_x = draw_tracked(layer, line2, big, W / 2, y2, track, color, visible)
        lime_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        # "REAL." glow once fully revealed
        if front >= len(line2):
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw_tracked(g, line2, big, W / 2, y2, track,
                         lambda i, c: with_alpha(LIME, 0.9 * fade_lines),
                         lambda i, c: c if i >= real_start else None)
            lime_layer.alpha_composite(g.filter(ImageFilter.GaussianBlur(18)))
        # scan line
        if front < len(line2) + 2:
            x0 = W / 2 - text_width(line2, big, track) / 2
            xs = x0 + text_width(line2[: int(min(front, len(line2)))], big, track)
            s = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(s).rectangle([xs, y2 - 10, xs + 4, y2 + 120], fill=LIME + (255,))
            lime_layer.alpha_composite(glow(s, 14, 2.0))
        img.alpha_composite(lime_layer)
        img.alpha_composite(layer)

    # Brand lock-up from f66.
    if f >= 68:
        p = ease_out(prog(f, 68, 10))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        half = 320 * p
        d.rectangle([W / 2 - half, 600, W / 2 + half, 603], fill=LIME + (255,))
        img.alpha_composite(glow(layer, 10, 1.5))

        wm = font("InterDisplay-Bold.otf", 120)
        a = ease_out(prog(f, 72, 10))
        if a > 0:
            t = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dy = 24 * (1 - a)
            # Placeholder wordmark: swap for the official FundingRock logo in AE.
            draw_tracked(t, "FundingRock", wm, W / 2, 430 + dy, 0, lambda i, c: with_alpha(WHITE, a))
            img.alpha_composite(t)
        sub = font("Inter-Medium.otf", 30)
        a2 = ease_out(prog(f, 80, 10))
        if a2 > 0:
            t = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw_tracked(t, "SIMULATED TRADING.  PERFORMANCE-BASED REWARDS.", sub, W / 2, 640, 6,
                         lambda i, c: with_alpha(GREY, a2))
            img.alpha_composite(t)
    return img


# =====================================================================
# 2. Telemetry overlay for the overtake freeze (alpha, 2s)
# =====================================================================
def telemetry(f):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lime_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl, dt = ImageDraw.Draw(lime_l), ImageDraw.Draw(txt)
    p = ease_out(prog(f, 0, 6))

    # Corner brackets closing in on the action.
    m = 140 + 60 * (1 - p)
    L = 70
    for (x, y, sx, sy) in [(m, m * 0.6, 1, 1), (W - m, m * 0.6, -1, 1),
                           (m, H - m * 0.6, 1, -1), (W - m, H - m * 0.6, -1, -1)]:
        dl.line([(x, y), (x + sx * L, y)], fill=LIME + (int(255 * p),), width=4)
        dl.line([(x, y), (x, y + sy * L)], fill=LIME + (int(255 * p),), width=4)

    lab = font("Inter-SemiBold.otf", 22)
    num = font("InterDisplay-Black.otf", 120)
    mid = font("InterDisplay-Bold.otf", 54)
    a = ease_out(prog(f, 2, 6))
    x0 = 200 - 40 * (1 - a)

    # Gear
    dt.text((x0, 690), "GEAR", font=lab, fill=with_alpha(GREY, a))
    dt.text((x0 - 6, 712), "7", font=num, fill=with_alpha(WHITE, a))
    # Speed counting up
    spd = int(287 + 25 * ease_out(prog(f, 2, 18)))
    dt.text((x0 + 130, 690), "KM/H", font=lab, fill=with_alpha(GREY, a))
    dt.text((x0 + 128, 712), f"{spd}", font=num, fill=with_alpha(WHITE, a))
    # Throttle / brake bars
    bx, by = x0 + 470, 735
    dt.text((bx, by - 45), "THR", font=lab, fill=with_alpha(GREY, a))
    dt.text((bx, by + 45), "BRK", font=lab, fill=with_alpha(GREY, a))
    thr = ease_out(prog(f, 3, 10))
    dt.rectangle([bx + 70, by - 40, bx + 370, by - 22], outline=with_alpha(GREY, a * 0.6), width=2)
    dl.rectangle([bx + 72, by - 38, bx + 72 + 296 * thr, by - 24], fill=with_alpha(LIME, a))
    dt.rectangle([bx + 70, by + 50, bx + 370, by + 68], outline=with_alpha(GREY, a * 0.6), width=2)

    # Delta, right side
    a3 = ease_out(prog(f, 5, 6))
    xr = W - 200 + 40 * (1 - a3)
    dt.text((xr, 690), "DELTA", font=lab, fill=with_alpha(GREY, a3), anchor="ra")
    dt.text((xr, 722), "-0.214", font=mid, fill=with_alpha(LIME, a3), anchor="ra")
    dt.text((xr, 800), "LAP 58 / 58", font=lab, fill=with_alpha(WHITE, a3), anchor="ra")

    # OVERTAKE tag top-left (black text on lime box)
    a4 = ease_out(prog(f, 4, 5))
    if a4 > 0:
        tag = font("InterDisplay-Black.otf", 34)
        w = 40 + text_width("OVERTAKE", tag, 6)
        tx, ty = 200, 170
        dl.rectangle([tx, ty, tx + w * a4, ty + 58], fill=LIME + (255,))
        if a4 > 0.6:
            draw_tracked(txt, "OVERTAKE", tag, tx + w / 2, ty + 8, 6, lambda i, c: (0, 0, 0, 255))

    # Blink indicator dot
    if (f // 6) % 2 == 0:
        dl.ellipse([W - 230, 172, W - 212, 190], fill=LIME + (int(255 * p),))
        dt.text((W - 200, 168), "LIVE", font=lab, fill=with_alpha(WHITE, p), anchor="la")

    img.alpha_composite(glow(lime_l, 8, 1.2))
    img.alpha_composite(txt)
    return img


# =====================================================================
# 3. Reward UI panel (alpha, 3s) - corner-pin onto the monitor or use full screen
# =====================================================================
def reward_ui(f):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p = ease_out(prog(f, 0, 8))
    pw, ph = 1100 * (0.94 + 0.06 * p), 460 * (0.94 + 0.06 * p)
    x0, y0 = W / 2 - pw / 2, H / 2 - ph / 2
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=36,
                                            fill=(10, 12, 10, int(235 * p)))
    img.alpha_composite(panel)
    border = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle([x0, y0, x0 + pw, y0 + ph], radius=36,
                                             outline=with_alpha(LIME, 0.55 * p), width=3)
    img.alpha_composite(glow(border, 16, 1.4))

    # Check icon: circle draws, then tick.
    cx, cy, r = W / 2, y0 + 140, 58
    ic = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    di = ImageDraw.Draw(ic)
    c = ease_out(prog(f, 6, 10))
    if c > 0:
        di.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * c, fill=LIME + (255,), width=6)
    t = ease_out(prog(f, 14, 6))
    if t > 0:
        pts = [(cx - 26, cy + 2), (cx - 8, cy + 22), (cx + 28, cy - 20)]
        seg1 = min(1, t * 2)
        e1 = (pts[0][0] + (pts[1][0] - pts[0][0]) * seg1, pts[0][1] + (pts[1][1] - pts[0][1]) * seg1)
        di.line([pts[0], e1], fill=LIME + (255,), width=8)
        if t > 0.5:
            s2 = (t - 0.5) * 2
            e2 = (pts[1][0] + (pts[2][0] - pts[1][0]) * s2, pts[1][1] + (pts[2][1] - pts[1][1]) * s2)
            di.line([pts[1], e2], fill=LIME + (255,), width=8)
    img.alpha_composite(glow(ic, 14, 1.6))

    # Text
    lab = font("Inter-SemiBold.otf", 24)
    big = font("InterDisplay-Black.otf", 64)
    a = ease_out(prog(f, 16, 8))
    if a > 0:
        tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_tracked(tl, "SIMULATED  ·  RESULT", lab, W / 2, y0 + 230, 8,
                     lambda i, ch: with_alpha(GREY, a))
        dy = 14 * (1 - a)
        draw_tracked(tl, "PERFORMANCE REWARD EARNED", big, W / 2, y0 + 285 + dy, 4,
                     lambda i, ch: with_alpha(WHITE, a))
        img.alpha_composite(tl)
    u = ease_out(prog(f, 22, 10))
    if u > 0:
        ul = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ul).rectangle([W / 2 - 260 * u, y0 + 390, W / 2 + 260 * u, y0 + 394],
                                     fill=LIME + (255,))
        img.alpha_composite(glow(ul, 10, 1.6))
    return img


# =====================================================================
# 4. Lime wipe line for the sim -> trading-room morph (alpha, 1s)
# =====================================================================
def lime_wipe(f, n=24):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = -80 + (W + 160) * ease_in_out(clamp(f / (n - 1)))
    core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(core)
    d.rectangle([x - 3, 0, x + 3, H], fill=LIME + (255,))
    fat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(fat).rectangle([x - 40, 0, x + 40, H], fill=LIME + (110,))
    wide = fat.filter(ImageFilter.GaussianBlur(70))
    a = wide.getchannel("A").point(lambda v: min(255, int(v * 1.6)))
    wide.putalpha(a)
    img.alpha_composite(wide)
    img.alpha_composite(glow(core, 14, 2.0))
    # hot white centre
    ImageDraw.Draw(img).rectangle([x - 1, 0, x + 1, H], fill=(255, 255, 230, 255))
    return img


def lime_flash(f):
    """2-frame lime hit for gear shifts and impacts (blend: Screen)."""
    return Image.new("RGBA", (W, H), LIME + (200 if f == 0 else 110,))


JOBS = {
    "lime_flash": (lime_flash, 2, True),
    "endcard": (end_card, 120, False),
    "telemetry_overlay": (telemetry, 48, True),
    "reward_ui": (reward_ui, 72, True),
    "lime_wipe": (lime_wipe, 24, True),
}


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for name, (fn, frames, alpha) in JOBS.items():
        if only and name != only:
            continue
        enc = Encoder(str(out / f"{name}.mov"), str(out / f"{name}_preview.mp4"), alpha)
        for f in range(frames):
            enc.write(fn(f))
        enc.close()
        print("wrote", name, frames, "frames")


if __name__ == "__main__":
    main()

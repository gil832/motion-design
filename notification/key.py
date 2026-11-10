"""Key the green phone screen out of the hand/phone plate.

Input:  up.png  (photoreal hand holding a phone with a chroma-green screen)
Output: plate_clean.jpg (screen blacked out, backlight graded to brand lime),
        matte.png (screen alpha), plate.js (screen corner quad for scene16.html)
"""
import json

import numpy as np
from PIL import Image, ImageFilter

im = Image.open('up.png').convert('RGB'); W, H = im.size
a = np.asarray(im).astype(np.float32)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
d = g - np.maximum(r, b)
scr = (g > 200) & (d > 170)                      # bright pure screen green only
ys, xs = np.nonzero(scr); y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
rows = np.arange(int(y0 + .15 * (y1 - y0)), int(y0 + .85 * (y1 - y0)))
L = np.array([np.nonzero(scr[y])[0].min() for y in rows]); R = np.array([np.nonzero(scr[y])[0].max() for y in rows])
cols = np.arange(int(x0 + .15 * (x1 - x0)), int(x0 + .85 * (x1 - x0)))
Tp = np.array([np.nonzero(scr[:, x])[0].min() for x in cols]); Bt = np.array([np.nonzero(scr[:, x])[0].max() for x in cols])


def rfit(u, v):
    k = np.abs(v - np.median(v)) < 12
    for _ in range(3):
        m, c = np.polyfit(u[k], v[k], 1); res = np.abs(v - (m * u + c)); k = res < max(3, np.percentile(res, 60))
    return m, c


mL, cL = rfit(rows, L); mR, cR = rfit(rows, R); mT, cT = rfit(cols, Tp); mB, cB = rfit(cols, Bt)


def isect(mx, cx, my, cy):
    y = (my * cx + cy) / (1 - my * mx); return [float(mx * y + cx), float(y)]


p = 3
C = [isect(mL, cL - p, mT, cT - p), isect(mR, cR + p, mT, cT - p), isect(mR, cR + p, mB, cB + p), isect(mL, cL - p, mB, cB + p)]
open('plate.js', 'w').write('window.PLATE = ' + json.dumps({'w': W, 'h': H, 'corners': C}) + ';\n')

soft = np.clip((d - 30) / 90, 0, 1)
grow = np.asarray(Image.fromarray((scr * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9))) > 0
alpha = np.where(grow, np.maximum(soft, scr * 1.0), 0)
m = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
mm = Image.new('RGBA', (W, H), (255, 255, 255, 0)); mm.putalpha(m); mm.save('matte.png', optimize=True)
k = (np.asarray(m).astype(np.float32) / 255)[..., None]
g2 = np.where(grow, np.minimum(g, np.maximum(r, b) + 6), g)
# grade the green backlight toward brand lime (#d6f21d): lift red where green dominates (skin unaffected)
gw = np.clip((g2 - r) / 60.0, 0, 1) * (1 - grow)
r2 = r + gw * np.maximum(0, 0.84 * g2 - r)
b2 = b * (1 - 0.6 * gw)
g3 = g2 * (1 - 0.12 * gw)
clean = np.stack([r2, g3, b2], -1) * (1 - k) + np.array([2, 3, 3]) * k
Image.fromarray(np.clip(clean, 0, 255).astype(np.uint8)).save('plate_clean.jpg', quality=93)
print(W, H, C)

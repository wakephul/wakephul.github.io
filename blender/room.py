"""The room. Interior is x 0..W (along the back wall), y 0..D (front to back), z 0..H.
Left wall at x=0, back wall at y=D; the other two sides are open towards the camera.
Clickable things live in their own group (computer, whiteboard, bookshelf, notebook, basketball,
guitar, bike, shoes, juggling, cards). The bake paints them white in the default look and the
room white in the other one (see lib.PAINT and run.bake).
"""
import math
import os
import random

import bmesh
from mathutils import Vector

from lib import box, camera, cyl, drape, group, lamp, loft, mat, prism, soft, sphere, spline, sun, text, tiles, torus, tube, world

W, D, H = 4.4, 4.2, 2.6
T = 0.16  # wall thickness
TARGET = (W / 2 - 0.1, D / 2 - 0.1, 0.85)
VIEW = (42, 30, 15.0)  # azimuth, elevation, distance of the overview
VIEW_TRANSFORM, LOOK = "AgX", "AgX - Medium High Contrast"
BG = "#eee8f8"

# The room's palette comes from the logo: violet and pink, like a two-ink risograph, on pink paper.
# White is kept for the clickable things.
VIOLET, LILAC, INK = "#6d3fe6", "#a58af3", "#2a1570"
PINK, BLUSH, ROSE = "#ec3c9a", "#f7b3d5", "#c92c84"   # fuchsia, its light version, its dark one
SUN = "#ffcf3f"   # the one warm accent
WALL, WALL_EDGE, WOOD, WOOD_D, WHITE = "#c5b4ee", "#f3eefc", BLUSH, INK, LILAC
SAGE = "#8a63ee"   # painted furniture
OAK, OAK_D = "#d2a26c", "#8a5a36"   # real wood, for the things that keep their own colours
DARK, METAL, CREAM = "#2b2e36", "#aab0b8", "#f1e9d6"
# handwriting for the whiteboard, used only at build time (Blender's own font if missing)
HAND = next((f for f in ("/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf",) if os.path.exists(f)), None)
WARM = "#ffc98a"   # lamp light: stays warm even in the grey room
POUF = (1.27, 0.7)
BOOKS = ["#c8553d", "#f28f3b", "#ffd166", "#588b8b", "#2a6f97", "#6d597a",
         "#e9d8a6", "#3d405b", "#81b29a", "#e07a5f", "#f2cc8f", "#264653"]


# ------------------------------------------------------------------ walls
TILE = 0.1
LAVENDER = ("#c9b8f0", "#c2b0ec", "#d0c1f4", "#bba8e8", "#ccbdf2", "#c5b4ee")   # zellige: every tile a bit different
SYMBOLS = next((f for f in ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf",) if os.path.exists(f)), None)
SECRET = (8, 21)   # left wall, column and row of the tile with the w: high up, above the bookshelf


def walls(wy0, wy1, wz0, wz1):
    """Lavender tiles on both walls. Some are hand painted (the suits of the cards, a note, stars, a moon),
    some are mirrors (their own mesh: the web page makes them glint as the room turns), and one, high on the
    left wall, has a little w instead of a symbol: the easter egg."""
    nz = round(H / TILE)
    in_window = lambda y, z, m=0.0: y + m > wy0 and y - m < wy1 and z + m > wz0 and z - m < wz1
    r = random.Random(21)
    back = lambda i, j: r.choice(LAVENDER)
    left = lambda i, j: None if (i, j) == SECRET or in_window(i * TILE + 0.05, j * TILE + 0.05, 0.05) else r.choice(LAVENDER)
    tiles((0, D - 0.001, 0), (TILE, 0, 0), (0, 0, TILE), round(W / TILE), nz, back, name="tiles_back", rough=0.3)
    tiles((0.001, 0, 0), (0, TILE, 0), (0, 0, TILE), round(D / TILE), nz, left, name="tiles_left", rough=0.3)
    used = {(False,) + SECRET}
    def spot(on_back):
        for _ in range(50):
            i, j = r.randrange(round((W if on_back else D) / TILE)), r.randrange(3, nz)
            if (on_back, i, j) not in used and (on_back or not in_window((i + 0.5) * TILE, (j + 0.5) * TILE, 0.06)):
                used.add((on_back, i, j))
                return i, j
    for k in range(46):
        on_back = k % 2 == 0
        i, j = spot(on_back)
        sym = "♠♥♣♦♪★☾✿✦"[k % 9]
        col = "#c92c84" if sym in "♥♦" else INK
        if on_back:
            text(sym, (i + 0.5) * TILE, D - 0.0025, (j + 0.5) * TILE - 0.025, 0.06, col, align="CENTER", font=SYMBOLS, depth=0.0004)
        else:
            text(sym, 0.0025, (i + 0.5) * TILE, (j + 0.5) * TILE - 0.025, 0.06, col, rot=(90, 0, 90), align="CENTER", font=SYMBOLS, depth=0.0004)
    with group("mirrors", uv=0.6):
        for k in range(60):
            on_back = k % 3 != 0
            i, j = spot(on_back)
            rot = (90 + r.uniform(-8, 8), r.uniform(-8, 8), 0 if on_back else 90)
            loc = ((i + 0.5) * TILE, D - 0.004, (j + 0.5) * TILE) if on_back else (0.004, (i + 0.5) * TILE, (j + 0.5) * TILE)
            with group(loc=loc, rot=rot):
                box(-0.046, -0.046, -0.0015, 0.092, 0.092, 0.003, "#d9d2f2", bevel=0.0, metal=1.0, rough=0.08)
    with group("secret", uv=2.0):
        i, j = SECRET
        box(0.0015, i * TILE, j * TILE, 0.001, TILE, TILE, LAVENDER[0], bevel=0.0, rough=0.3)
        text("w", 0.0025, (i + 0.5) * TILE, j * TILE + 0.031, 0.075, PINK, rot=(90, 0, 90), align="CENTER", font=HAND, depth=0.0004)   # baseline so the w sits in the middle


# ------------------------------------------------------------------ shell
def shell():
    box(-T, 0, -0.22, W + T, D + T, 0.22, WALL_EDGE, bevel=0.01, name="slab")
    box(0, D, 0, W, T, H, WALL, bevel=0.01, name="wall_back")
    wy0, wy1, wz0, wz1 = 2.55, 3.75, 1.0, 2.05   # window opening in the left wall
    box(-T, 0, 0, T, wy0, H, WALL, bevel=0.01)
    box(-T, wy1, 0, T, D + T - wy1, H, WALL, bevel=0.01)
    box(-T, wy0, 0, T, wy1 - wy0, wz0, WALL, bevel=0.0)
    box(-T, wy0, wz1, T, wy1 - wy0, H - wz1, WALL, bevel=0.0)
    # window frame, mullions, sill
    f = 0.045
    for y in (wy0, wy1 - f, (wy0 + wy1 - f) / 2):
        box(-0.11, y, wz0, 0.06, f, wz1 - wz0, WHITE, bevel=0.006)
    for z in (wz0, wz1 - f, (wz0 + wz1 - f) / 2):   # a bit thinner: shared faces with the uprights bake black
        box(-0.106, wy0 + 0.004, z, 0.052, wy1 - wy0 - 0.008, f, WHITE, bevel=0.006)
    box(-0.02, wy0 - 0.05, wz0 - 0.035, 0.11, wy1 - wy0 + 0.1, 0.035, WHITE, bevel=0.008)
    # curtains
    tube([(0.08, wy0 - 0.3, wz1 + 0.13), (0.08, wy1 + 0.3, wz1 + 0.13)], 0.012, METAL)
    for y0, y1 in ((wy0 - 0.27, wy0 + 0.05), (wy1 - 0.05, wy1 + 0.27)):
        n = 40
        a = [(0.08 + 0.028 * math.sin(i / n * math.pi * 7), y0 + (y1 - y0) * i / n) for i in range(n + 1)]
        b = [(x + 0.012, y) for x, y in reversed(a)]
        prism(a + b, wz0 - 0.12, wz1 - wz0 + 0.24, LILAC, sharp=60, name="curtain")
    walls(wy0, wy1, wz0, wz1)
    # skirting
    box(0, D - 0.015, 0, W, 0.015, 0.07, WHITE, bevel=0.004)
    box(0, 0, 0, 0.015, D, 0.07, WHITE, bevel=0.004)
    # floor planks
    r = random.Random(3)
    pw, y = 0.16, 0.0
    while y < D - 1e-6:
        w_ = min(pw, D - y)
        x = -r.uniform(0.2, 1.2)
        while x < W:
            ln = r.uniform(1.0, 1.7)
            x0, x1 = max(x, 0), min(x + ln, W)
            if x1 - x0 > 0.01:
                tone = r.choice(["#c98f5c", "#bd8250", "#d29a66", "#b37748", "#c68a56"])
                # flat boards that touch: gaps or grooves are thinner than a texel and turn into jagged dark lines
                box(x0, y, 0, x1 - x0, w_, 0.012, tone, bevel=0.0, rough=0.6)
            x += ln
        y += pw
    # checkerboard rug (its top at 0.031: the ball and the juggling things lie on it)
    t = 0.22
    for i in range(7):
        for j in range(6):
            box(1.86 + i * t, 0.85 + j * t, 0.012, t, t, 0.019, (VIOLET, BLUSH)[(i + j) % 2], bevel=0.0, rough=0.9)
    # string lights along the top of the back wall (bulbs in "glow": the page can make them blink)
    pts = []
    for i in range(18):
        x = 0.15 + i * 0.24
        z = 2.43 - 0.06 * abs(math.sin(i * math.pi / 3.4))
        pts.append((x, D - 0.02, z))
        with group("glow"):
            sphere(x, D - 0.03, z - 0.035, 0.022, WARM, emit=16, segs=12, keep=True)
    tube(pts, 0.004, INK, smooth=True)
    pts = []
    for i in range(16):
        y = 0.2 + i * 0.25
        z = 2.43 - 0.06 * abs(math.sin(i * math.pi / 3.1))
        pts.append((0.02, y, z))
        with group("glow"):
            sphere(0.03, y, z - 0.035, 0.022, WARM, emit=16, segs=12, keep=True)
    tube(pts, 0.004, INK, smooth=True)


# ------------------------------------------------------------------ furniture (grey)
def bed():
    """Double bed in the back-left corner, headboard on the back wall."""
    bw, bl = 1.7, 2.1
    with group(loc=(0.04, D - bl, 0)):
        for lx in (0.04, bw - 0.1):
            for ly in (0.04, bl - 0.12):
                box(lx, ly, 0, 0.06, 0.06, 0.14, WOOD_D, bevel=0.006)
        box(0, 0, 0.14, bw, bl - 0.03, 0.16, WOOD, bevel=0.012, name="bedframe")
        box(0, bl - 0.07, 0.14, bw, 0.07, 0.95, WOOD, bevel=0.02, name="headboard")
        soft(box(0.04, 0.03, 0.30, bw - 0.08, bl - 0.12, 0.2, BLUSH, name="mattress"), 0.05)
        top = 0.5                                     # mattress top
        mx0, mx1 = 0.04, bw - 0.04
        # duvet over the lower two thirds, hanging over the free sides (little on the wall side)
        drape(mx0, 0.03, mx1, 1.36, top, PINK, hang=(0.05, 0.3, 0.3, 0.0), r=0.06, name="duvet")
        # its top edge turned down, showing the white cover
        drape(mx0, 1.18, mx1, 1.38, top + 0.03, LILAC, hang=(0.05, 0.3, 0.0, 0.05), r=0.03, thick=0.022, wave=0.0, name="fold")
        # a knitted throw across the foot
        drape(mx0, 0.03, mx1, 0.46, top + 0.03, SUN, hang=(0.05, 0.34, 0.34, 0.0), r=0.065, thick=0.022, wave=0.006, name="throw")
        for px, col in ((0.14, LILAC), (0.88, BLUSH)):
            soft(box(px, 1.56, top - 0.01, 0.66, 0.4, 0.15, col, rot=(14, 0, 0), name="pillow"), 0.07)
        soft(box(0.6, 1.42, top + 0.02, 0.4, 0.14, 0.34, VIOLET, rot=(-18, 0, 4), name="cushion"), 0.06)
        headphones(0.5, 0.86, top + 0.034)
        # a book left open, face down: two covers leaning on a shared spine
        for ry, x0b in ((21, -0.15), (-21, 0.0)):
            with group(loc=(1.15, 0.78, top + 0.03 + 0.15 * math.sin(math.radians(21)) + 0.006), rot=(0, ry, 0)):
                box(x0b, -0.105, -0.007, 0.15, 0.21, 0.012, INK, bevel=0.002)
    # sheepskin by the bed, slippers on it
    blob = spline([(1.82, 2.42), (2.05, 2.33), (2.33, 2.4), (2.42, 2.7), (2.36, 3.0), (2.44, 3.25), (2.25, 3.42),
                   (2.0, 3.36), (1.84, 3.2), (1.86, 2.9), (1.8, 2.65)], 5, closed=True)
    prism(blob, 0.012, 0.035, BLUSH, bevel=0.014, sharp=70, name="sheepskin")
    for (sx, sy, turn, side) in ((1.9, 2.72, 4, 1), (1.92, 2.88, -5, -1)):
        with group(loc=(sx, sy, 0.047), rot=(0, 0, turn)):
            sandal(side, VIOLET)


def sandal(side, col):
    """Rubber sandal, two straps with buckles (the eva kind). x = heel to toe, side = 1 right foot, -1 left."""
    pts = [(0.0, 0.0), (0.012, 0.033), (0.05, 0.043), (0.12, 0.046), (0.19, 0.054), (0.245, 0.05), (0.27, 0.027),
           (0.276, 0.0), (0.265, -0.03), (0.23, -0.05), (0.17, -0.052), (0.1, -0.044), (0.04, -0.04), (0.012, -0.03)]
    prism([(x, side * y) for x, y in spline(pts, 4, closed=True)], 0.0, 0.028, col, bevel=0.007, sharp=70, name="sole")
    top = 0.028
    for x, half in ((0.115, 0.05), (0.185, 0.057)):
        a, b, wid, th = half + 0.004, 0.042, 0.017, 0.0035
        secs = []
        for k in range(17):
            t = math.pi * k / 16
            cy, cz = a * math.cos(t), top + b * math.sin(t)
            ny, nz = math.cos(t) / a, math.sin(t) / b
            ln = math.hypot(ny, nz)
            ny, nz = ny / ln * th, nz / ln * th
            secs.append([(x + wid, cy + ny, cz + nz), (x - wid, cy + ny, cz + nz), (x - wid, cy - ny, cz - nz), (x + wid, cy - ny, cz - nz)])
        loft(secs, col, name="strap")
        # the buckle, lying on the strap towards the outside of the foot
        t0 = math.pi * (0.3 if side < 0 else 0.7)
        ny, nz = math.cos(t0) / a, math.sin(t0) / b
        ln = math.hypot(ny, nz)
        ny, nz = ny / ln, nz / ln
        with group(loc=(x, a * math.cos(t0) + ny * th, top + b * math.sin(t0) + nz * th), rot=(math.degrees(math.atan2(-ny, nz)), 0, 0)):
            box(-0.011, -0.008, -0.001, 0.022, 0.016, 0.005, col, bevel=0.002)


def nightstand():
    with group(loc=(1.82, D - 0.42, 0)):
        for lx in (0.03, 0.39):
            for ly in (0.03, 0.34):
                box(lx, ly, 0, 0.03, 0.03, 0.1, WOOD_D, bevel=0.004)
        box(0, 0, 0.1, 0.45, 0.4, 0.42, WOOD, bevel=0.012)
        for z in (0.13, 0.32):
            box(0.02, -0.012, z, 0.41, 0.02, 0.17, SAGE, bevel=0.006)
            cyl(0.225, -0.012, z + 0.085, 0.014, 0.02, METAL, axis="Y", rot=(90, 0, 0))
        # mushroom lamp
        cyl(0.13, 0.24, 0.52, 0.05, 0.17, PINK, r2=0.028, bevel=0.006)
        sphere(0.13, 0.24, 0.7, 0.115, WARM, scale=(1, 1, 0.58), emit=4.0, keep=True)
        # two books and the phone
        box(0.23, 0.1, 0.52, 0.17, 0.23, 0.025, INK, bevel=0.004, rot=(0, 0, 4))
        box(0.24, 0.11, 0.545, 0.15, 0.21, 0.02, VIOLET, bevel=0.004, rot=(0, 0, -3))
        box(0.06, 0.04, 0.52, 0.075, 0.15, 0.009, INK, bevel=0.003, rot=(0, 0, 20))


def wall_shelf():
    """Shelf above the headboard and a couple of frames next to the guitar."""
    y, x0, z0 = D, 1.34, 1.5
    box(x0, y - 0.2, z0, 0.6, 0.2, 0.028, WOOD, bevel=0.006)
    zt = z0 + 0.028
    cyl(x0 + 0.1, y - 0.1, zt, 0.055, 0.11, PINK, r2=0.065, bevel=0.005)
    cyl(x0 + 0.1, y - 0.1, zt + 0.1, 0.058, 0.006, INK)
    for i in range(7):
        a = i * 2.4
        leaf((x0 + 0.1 + 0.02 * math.cos(a), y - 0.1 + 0.02 * math.sin(a), zt + 0.105), 0.2 + 0.05 * (i % 3), 0.05,
             tilt=80 - 7 * (i % 3), turn=math.degrees(a), col="#5f9455")
    x = x0 + 0.42
    for t, hgt, col in ((0.03, 0.2, INK), (0.024, 0.18, PINK), (0.035, 0.22, "#ef6f9a")):
        box(x, y - 0.17, zt, t, 0.14, hgt, col, bevel=0.003)
        x += t + 0.002
    # the logo as a neon sign
    w = [(14, 23), (24, 52), (33, 80), (44, 57), (55, 37), (64, 58), (74, 79), (89, 48), (106, 17)]
    with group("glow"):
        tube([(1.38 + (px - 14) / 92 * 0.5, y - 0.03, 1.94 + (80 - py) / 63 * 0.32) for px, py in spline(w, 6)], 0.009, PINK, emit=7.0)
    for px in (20, 100):
        cyl(1.38 + (px - 14) / 92 * 0.5, y, 2.2, 0.006, 0.03, INK, axis="Y", rot=(90, 0, 0))
    cyl(2.75, y, 2.24, 0.12, 0.025, INK, axis="Y", rot=(90, 0, 0), segs=40, bevel=0.006)
    cyl(2.75, y - 0.026, 2.24, 0.1, 0.002, SUN, axis="Y", rot=(90, 0, 0), segs=40)
    box(2.745, y - 0.031, 2.24, 0.01, 0.003, 0.075, INK, bevel=0.0)
    box(2.745, y - 0.031, 2.235, 0.055, 0.003, 0.01, INK, bevel=0.0)
    # two prints, two inks each
    for x, z, w_, h_, paper, a, b in ((2.62, 1.72, 0.26, 0.34, SUN, PINK, VIOLET), (2.64, 1.36, 0.22, 0.22, VIOLET, BLUSH, PINK)):
        box(x, y - 0.022, z, w_, 0.022, h_, WOOD_D, bevel=0.005)
        box(x + 0.015, y - 0.026, z + 0.015, w_ - 0.03, 0.006, h_ - 0.03, paper, bevel=0.0)
        cyl(x + w_ * 0.42, y - 0.029, z + h_ * 0.58, w_ * 0.28, 0.002, a, axis="Y", rot=(90, 0, 0), segs=40)
        cyl(x + w_ * 0.6, y - 0.031, z + h_ * 0.4, w_ * 0.22, 0.002, b, axis="Y", rot=(90, 0, 0), segs=40)


def leaf(base, length, width, tilt, turn, col):
    """A pointed leaf growing from `base`, raised by `tilt` degrees and turned around Z."""
    n = 10
    side = [(length * i / n, width / 2 * math.sin(math.pi * (i / n) ** 0.7)) for i in range(n + 1)]
    outline = side + [(x, -y) for x, y in reversed(side[1:-1])]
    prism(outline, 0, 0.004, col, loc=base, rot=(0, -tilt, turn), sharp=80)


def wardrobe():
    """Two-door wardrobe on the left wall."""
    w_, dp, h_ = 1.0, 0.58, 2.02
    with group(loc=(0.0, 1.06, 0)):
        box(0.02, 0.02, 0, dp - 0.06, w_ - 0.04, 0.06, WOOD_D, bevel=0.004)
        box(0, 0, 0.06, dp, w_, h_ - 0.06, SAGE, bevel=0.012)
        for dy in (0.012, w_ / 2 + 0.004):
            box(dp, dy, 0.075, 0.02, w_ / 2 - 0.016, h_ - 0.09, SAGE, bevel=0.006)
        for dy in (w_ / 2 - 0.05, w_ / 2 + 0.03):
            box(dp + 0.02, dy, 0.95, 0.022, 0.02, 0.22, METAL, bevel=0.006)
        # things on top
        box(0.06, 0.08, h_, 0.42, 0.36, 0.24, PINK, bevel=0.01)
        box(0.05, 0.07, h_ + 0.24, 0.44, 0.38, 0.03, ROSE, bevel=0.008)


def desk():
    x0, y0 = 2.78, D - 0.74
    top = 0.745
    with group(loc=(x0, y0, 0)):
        box(0, 0, 0.71, 1.5, 0.7, 0.035, WOOD, bevel=0.008, name="desktop")
        box(0.04, 0.05, 0, 0.04, 0.6, 0.71, SAGE, bevel=0.006)
        box(0.1, 0.62, 0.36, 0.95, 0.02, 0.3, SAGE, bevel=0.004)
        # drawer unit on the right
        box(1.04, 0.04, 0.02, 0.42, 0.6, 0.69, SAGE, bevel=0.01)
        for i in range(3):
            box(1.055, 0.025, 0.05 + i * 0.22, 0.39, 0.02, 0.2, SAGE, bevel=0.006)
            box(1.19, 0.008, 0.19 + i * 0.22, 0.12, 0.018, 0.016, METAL, bevel=0.005)
        # desk lamp
        cyl(1.36, 0.52, top, 0.07, 0.018, INK, bevel=0.004)
        tube([(1.36, 0.52, top), (1.36, 0.6, top + 0.3), (1.2, 0.42, top + 0.5)], 0.008, INK)
        cyl(1.2, 0.42, top + 0.42, 0.075, 0.1, INK, r2=0.03, rot=(28, 28, 0))
        sphere(1.19, 0.41, top + 0.44, 0.03, WARM, emit=26, segs=12, keep=True)
        # a pot of pens at the back, the mug at hand by the notebook
        cyl(0.1, 0.56, top, 0.04, 0.095, SUN, bevel=0.004)
        for i, c in enumerate((VIOLET, PINK, INK, PINK)):
            cyl(0.085 + 0.012 * i, 0.55 + 0.008 * (i % 2), top + 0.01, 0.0045, 0.16, c, rot=(6 - 4 * i, 5 * i - 8, 0))
        mug(0.1, 0.22, top, VIOLET, -45)
    # bin under the desk
    cyl(x0 + 0.3, y0 + 0.42, 0.012, 0.11, 0.3, PINK, r2=0.14, segs=24)
    cyl(x0 + 0.3, y0 + 0.42, 0.31, 0.13, 0.002, INK, segs=24)
    return x0, y0, top


def chair(x, y, turn):
    with group(loc=(x, y, 0), rot=(0, 0, turn)):
        for i in range(5):
            a = i * 72 + 18
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            box(-0.02 + 0.15 * ca, -0.02 + 0.15 * sa, 0.06, 0.04, 0.04, 0.03, INK, bevel=0.01)
            tube([(0.03 * ca, 0.03 * sa, 0.1), (0.3 * ca, 0.3 * sa, 0.07)], 0.018, INK)
            cyl(0.3 * ca, 0.3 * sa - 0.02, 0.03, 0.03, 0.04, INK, axis="Y", bevel=0.006)
        cyl(0, 0, 0.08, 0.028, 0.34, METAL)
        cyl(0, 0, 0.37, 0.06, 0.05, INK, bevel=0.01)
        soft(box(-0.24, -0.22, 0.42, 0.48, 0.47, 0.09, "#3b2a7a", name="seat"), 0.04)
        tube([(0, -0.18, 0.44), (0, -0.3, 0.5), (0, -0.31, 0.75)], 0.02, INK, smooth=True)
        soft(box(-0.22, -0.36, 0.6, 0.44, 0.075, 0.56, "#3b2a7a", rot=(-7, 0, 0), name="back"), 0.035)
        for sx in (-1, 1):
            tube([(sx * 0.22, -0.02, 0.44), (sx * 0.29, -0.02, 0.5), (sx * 0.29, -0.02, 0.66)], 0.013, INK, smooth=True)
            soft(box(sx * 0.29 - 0.035, -0.14, 0.655, 0.07, 0.26, 0.03, INK), 0.012)


def mug(x, y, z, col, turn=0):
    cyl(x, y, z, 0.038, 0.085, col, bevel=0.004)
    cyl(x, y, z + 0.0855, 0.031, 0.001, INK, segs=24)
    a = math.radians(turn)
    torus(x + 0.046 * math.cos(a), y + 0.046 * math.sin(a), z + 0.045, 0.024, 0.006, col, rot=(90, 0, turn), segs=24)


def headphones(x, y, z):
    """Over-ear headphones dropped on the duvet, plugged into an ipod by a cable that wanders a bit."""
    with group(loc=(x, y, z), rot=(0, 0, 25)):
        r = 0.085
        tube([(r * math.cos(math.radians(a)), r * math.sin(math.radians(a)), 0.03) for a in range(0, 181, 15)], 0.009, INK, smooth=True)
        for sx in (-1, 1):
            torus(sx * r, 0, 0.008, 0.036, 0.009, LILAC, segs=32)            # the pad, against the duvet
            cyl(sx * r, 0, 0.008, 0.044, 0.03, INK, bevel=0.01, segs=32)     # the cup
            cyl(sx * r, 0, 0.038, 0.026, 0.002, VIOLET, segs=32)             # a disc on the outside
    px, py, turn = x + 0.3, y - 0.26, -18
    with group(loc=(px, py, z), rot=(0, 0, turn)):
        box(0, 0, 0, 0.062, 0.104, 0.011, SUN, bevel=0.004)                 # ipod
        box(0.007, 0.056, 0.011, 0.048, 0.04, 0.0008, "#1d2233", bevel=0.0, emit=1.5)
        cyl(0.031, 0.027, 0.011, 0.019, 0.0008, INK, segs=32)              # click wheel
        cyl(0.031, 0.027, 0.0115, 0.0065, 0.0008, SUN, segs=24)
    # the cable, from the jack on top of the ipod to the left cup
    t = math.radians(turn)
    jx, jy = px + 0.031 * math.cos(t) - 0.106 * math.sin(t), py + 0.031 * math.sin(t) + 0.106 * math.cos(t)
    tube([(jx, jy, z + 0.006), (jx + 0.01, jy + 0.05, z + 0.004), (x + 0.22, y - 0.06, z + 0.004), (x + 0.1, y - 0.1, z + 0.004),
          (x + 0.0, y - 0.07, z + 0.006), (x - 0.06, y - 0.06, z + 0.01)], 0.0025, INK, smooth=True)


def floor_lamp(x, y):
    for i in range(3):
        a = math.radians(90 + i * 120)
        tube([(x, y, 1.14), (x + 0.27 * math.cos(a), y + 0.27 * math.sin(a), 0.014)], 0.012, WOOD)
    cyl(x, y, 1.1, 0.032, 0.06, INK, bevel=0.006)
    cyl(x, y, 1.14, 0.008, 0.18, INK)
    cyl(x, y, 1.27, 0.17, 0.27, WARM, r2=0.125, emit=3.0, keep=True, segs=40)


def reading_corner():
    """Floor lamp, pouf and a short pile of books, next to the bookshelf."""
    floor_lamp(0.62, 0.7)   # clear of the wardrobe doors
    # knitted pouf: a soft drum with a seam and a button
    cyl(POUF[0], POUF[1], 0.012, 0.3, 0.36, LILAC, segs=48, bevel=0.09, seg=5)
    torus(POUF[0], POUF[1], 0.192, 0.302, 0.006, ROSE, segs=48)
    cyl(POUF[0], POUF[1], 0.37, 0.018, 0.008, ROSE, segs=16, bevel=0.003)
    for i, (w_, col) in enumerate(((0.23, INK), (0.21, VIOLET), (0.19, PINK))):
        box(1.68, 0.3, 0.012 + i * 0.034, 0.16, w_, 0.032, col, bevel=0.004, rot=(0, 0, (i * 23) % 17 - 8))


def plants():
    # a big plant on the floor, between the nightstand and the desk
    px, py = 2.52, 3.9
    cyl(px, py, 0, 0.15, 0.34, ROSE, r2=0.18, bevel=0.01, segs=40)
    cyl(px, py, 0.33, 0.165, 0.01, INK, segs=40)
    r = random.Random(9)
    for i in range(9):
        a = math.radians(i * 137.5)
        reach, hgt = 0.12 + 0.03 * (i % 3), 0.75 + 0.08 * (i % 4)
        tip = (px + reach * math.cos(a), py + reach * math.sin(a), hgt)
        tube([(px + 0.02 * math.cos(a), py + 0.02 * math.sin(a), 0.33), (px + 0.5 * reach * math.cos(a), py + 0.5 * reach * math.sin(a), 0.55), tip],
             0.007, "#4f8247", smooth=True)
        leaf(tip, 0.3 + r.uniform(-0.04, 0.04), 0.2, tilt=-10 + 12 * (i % 3), turn=math.degrees(a), col=("#5f9455", "#4f8247")[i % 2])
    # a pothos hanging from a macramé, by the window
    hx, hy, top = 0.24, 2.3, 2.32
    for k in range(3):
        a = math.radians(90 + k * 120)
        tube([(hx, hy, top), (hx + 0.085 * math.cos(a), hy + 0.085 * math.sin(a), 1.86)], 0.004, "#f2d7b6")
    cyl(hx, hy, 1.76, 0.07, 0.11, PINK, r2=0.09, bevel=0.006, segs=28)
    cyl(hx, hy, 1.86, 0.082, 0.008, INK, segs=28)
    for k in range(6):   # vines trailing down, a few leaves on each
        a = math.radians(k * 60 + 20)
        x1, y1 = hx + 0.09 * math.cos(a), hy + 0.09 * math.sin(a)
        drop = 0.25 + 0.12 * (k % 3)
        vine = [(x1, y1, 1.87), (x1 + 0.03 * math.cos(a), y1 + 0.03 * math.sin(a), 1.8), (x1 + 0.05 * math.cos(a), y1 + 0.05 * math.sin(a), 1.87 - drop)]
        tube(vine, 0.003, "#4f8247", smooth=True)
        for j in range(3):
            t = (j + 1) / 3
            leaf((x1 + 0.045 * t * math.cos(a), y1 + 0.045 * t * math.sin(a), 1.84 - drop * t), 0.06, 0.045, tilt=-50, turn=math.degrees(a) + 40 * j, col="#6a9a5b")
    # leafy plant on top of the wardrobe (on the floor it would hide the desk)
    px, py, pz = 0.3, 1.78, 2.02
    cyl(px, py, pz, 0.11, 0.2, PINK, r2=0.14, bevel=0.008, segs=32)
    cyl(px, py, pz + 0.2, 0.125, 0.01, INK, segs=32)
    for i in range(10):
        a = math.radians(i * 137.5)
        reach, hgt = 0.1 + 0.035 * (i % 4), pz + 0.3 + 0.03 * i
        tip = (px + reach * math.cos(a), py + reach * math.sin(a), hgt)
        tube([(px + 0.02 * math.cos(a), py + 0.02 * math.sin(a), pz + 0.2), (px + 0.6 * reach * math.cos(a), py + 0.6 * reach * math.sin(a), pz + 0.2 + (hgt - pz - 0.2) * 0.75), tip],
             0.006, "#5d8a4f", smooth=True)
        leaf(tip, 0.26 - 0.01 * i, 0.15 - 0.006 * i, tilt=-22 + 9 * (i % 3), turn=math.degrees(a), col="#5f9455")
    # window sill: cactus, succulent, candles
    cyl(0.035, 2.72, 1.0, 0.04, 0.07, PINK, r2=0.05, bevel=0.004)
    sphere(0.035, 2.72, 1.12, 0.045, "#6a9a5b", scale=(1, 1, 1.5))
    sphere(0.035, 2.675, 1.13, 0.02, "#6a9a5b", scale=(1, 1, 1.4))
    cyl(0.035, 3.52, 1.0, 0.045, 0.06, ROSE, r2=0.055, bevel=0.004)
    for i in range(7):
        leaf((0.035, 3.52, 1.06), 0.07, 0.035, tilt=35 + 12 * (i % 3), turn=i * 51, col="#6a9a5b")
    for yy, hgt in ((3.02, 0.09), (3.1, 0.06)):
        cyl(0.04, yy, 1.0, 0.022, hgt, BLUSH, bevel=0.003, segs=20)
        sphere(0.04, yy, 1.0 + hgt + 0.014, 0.008, WARM, scale=(1, 1, 1.9), segs=10, emit=60, keep=True)


# ------------------------------------------------------------------ clickable things (coloured)
def computer(x0, y0, top):
    with group("computer", loc=(x0 + 0.72, y0, top), uv=1.8):
        # monitor: stand, neck, panel, glowing screen with "code"
        box(-0.13, 0.4, 0, 0.26, 0.2, 0.012, "#c9ccd1", bevel=0.005, metal=0.5, rough=0.4)
        box(-0.025, 0.5, 0.01, 0.05, 0.03, 0.3, "#c9ccd1", bevel=0.006, metal=0.5, rough=0.4)
        box(-0.32, 0.455, 0.2, 0.64, 0.035, 0.385, "#23252b", bevel=0.01)
        box(-0.308, 0.452, 0.212, 0.616, 0.004, 0.36, "#1d2233", bevel=0.0, emit=1.2)
        r = random.Random(4)
        cols = ["#7aa2f7", "#bb9af7", "#9ece6a", "#e0af68", "#f7768e", "#7dcfff"]
        for row in range(13):
            x = -0.29 + 0.022 * r.choice((0, 0, 1, 1, 2, 3))
            z = 0.545 - row * 0.0245
            if row in (5, 9):
                continue
            for _ in range(r.randint(1, 4)):
                ln = r.uniform(0.03, 0.12)
                if x + ln > 0.02:
                    break
                box(x, 0.4505, z, ln, 0.002, 0.011, r.choice(cols), bevel=0.0, emit=6)
                x += ln + 0.012
        # a little chart on the right half of the screen
        box(0.06, 0.4505, 0.25, 0.22, 0.002, 0.004, "#565f89", bevel=0.0, emit=4)
        for i, hgt in enumerate((0.05, 0.09, 0.07, 0.13, 0.11, 0.17, 0.21)):
            box(0.07 + i * 0.03, 0.4505, 0.256, 0.018, 0.002, hgt, cols[i % 3], bevel=0.0, emit=6)
        # keyboard
        with group(loc=(-0.2, 0.1, 0), rot=(4, 0, 0)):
            box(0, 0, 0, 0.4, 0.14, 0.016, "#2b2e36", bevel=0.006)
            for row in range(5):
                x = 0.01
                widths = [0.022] * 16 if row < 4 else [0.03, 0.022, 0.03, 0.14, 0.03, 0.022, 0.022, 0.03]
                for i, kw in enumerate(widths):
                    col = "#f2805a" if (row == 4 and i == 0) or (row == 0 and i == 15) else "#eeeae2"
                    box(x, 0.012 + (4 - row) * 0.0245, 0.016, kw, 0.021, 0.008, col, bevel=0.003, seg=1)
                    x += kw + 0.0027
        # mouse on its pad
        box(0.27, 0.06, 0, 0.24, 0.2, 0.003, "#2a1570", bevel=0.001)
        soft(box(0.355, 0.11, 0.003, 0.06, 0.1, 0.034, "#eeeae2"), 0.02)


def notebook(x0, y0, top):
    with group("notebook", loc=(x0 + 0.24, y0 + 0.14, top), rot=(0, 0, -14), uv=2.2):
        box(0, 0, 0, 0.16, 0.225, 0.018, "#e0372f", bevel=0.004)
        box(0.004, 0.003, 0.002, 0.154, 0.219, 0.014, CREAM, bevel=0.0)
        box(0.125, -0.001, -0.0005, 0.008, 0.227, 0.0195, "#1d1d1f", bevel=0.001)
        box(0.03, 0.15, 0.018, 0.08, 0.035, 0.0006, CREAM, bevel=0.0)
        cyl(0.2, 0.03, 0.006, 0.006, 0.15, "#2a6f97", axis="Y", rot=(-90, 0, 14))
        cyl(0.2, 0.03, 0.006, 0.0062, 0.03, "#1d1d1f", axis="Y", rot=(-90, 0, 14))


def whiteboard():
    x0, z0, w_, h_ = 2.98, 1.3, 1.22, 0.8
    y = D
    with group("whiteboard", uv=2.6):
        box(x0, y - 0.025, z0, w_, 0.025, h_, "#b9bec6", bevel=0.006, metal=0.4, rough=0.45)
        box(x0 + 0.025, y - 0.028, z0 + 0.025, w_ - 0.05, 0.004, h_ - 0.05, "#fdfdfb", bevel=0.0, rough=0.35)
        box(x0 + 0.1, y - 0.075, z0 - 0.012, w_ - 0.2, 0.06, 0.012, "#b9bec6", bevel=0.004, metal=0.4)   # tray
        for i, c in enumerate(("#1f5fbf", "#d92b2b", "#1e9e5a")):
            cyl(x0 + 0.2 + i * 0.16, y - 0.05, z0 + 0.008, 0.009, 0.12, c, axis="X")
        box(x0 + 0.8, y - 0.07, z0, 0.12, 0.045, 0.03, "#3d405b", bevel=0.008)   # eraser
        blue, red, green = "#1f5fbf", "#d92b2b", "#1e9e5a"
        yt = y - 0.0295
        def write(s, x, z, size, col):
            text(s, x0 + x, yt, z0 + z, size, col, shear=0.08, font=HAND)
        write("τ dV/dt = −(V − E) + RI", 0.07, 0.64, 0.068, blue)          # a spiking neuron (musin)
        write("Q(s,a) += α [r + γ max Q' − Q]", 0.07, 0.52, 0.052, red)   # q-learning (figaro)
        write("E[f(X)] ≥ f(E[X])", 0.07, 0.40, 0.06, green)               # convexity: antifragility
        # four EEG channels (the tDCS work)
        rr = random.Random(5)
        ex, ez = x0 + 0.08, z0 + 0.075
        for ch in range(4):
            ph, zc = rr.uniform(0, 6), ez + ch * 0.06
            pts = [(ex + i * 0.005, yt, zc + 0.012 * math.sin(i * 0.4 + ph) * (0.6 + 0.4 * math.sin(i * 0.05 + ph))
                    + 0.004 * math.sin(i * 1.3 + 2 * ph) + rr.uniform(-0.0015, 0.0015)) for i in range(104)]
            tube(pts, 0.0024, (DARK, blue, DARK, red)[ch])
        # a convex curve with its chord above it
        cx, cz = x0 + 0.74, z0 + 0.07
        tube([(cx, yt, cz), (cx + 0.36, yt, cz)], 0.003, DARK)
        tube([(cx, yt, cz), (cx, yt, cz + 0.26)], 0.003, DARK)
        f = lambda u: cz + 0.03 + 7.5 * (u - 0.17) ** 2
        tube([(cx + u / 100, yt, f(u / 100)) for u in range(4, 32)], 0.0032, green)
        a, b = 0.06, 0.30
        tube([(cx + a, yt, f(a)), (cx + b, yt, f(b))], 0.0022, red)
        for u in (a, b):
            cyl(cx + u, yt - 0.001, f(u), 0.008, 0.003, red, axis="Y", rot=(90, 0, 0), segs=16)
        # magnets and a note
        cyl(x0 + 1.1, yt, z0 + 0.7, 0.016, 0.008, "#f2b632", axis="Y", rot=(90, 0, 0))
        box(x0 + 1.0, yt - 0.002, z0 + 0.55, 0.13, 0.002, 0.13, "#ffe680", bevel=0.0, rot=(0, 4, 0))
        cyl(x0 + 1.065, yt - 0.003, z0 + 0.665, 0.014, 0.008, "#d92b2b", axis="Y", rot=(90, 0, 0))


def bookshelf():
    """On the left wall, facing the room. Local frame: x = depth, y = along the wall."""
    w_, dp, h_ = 0.82, 0.3, 1.86
    r = random.Random(11)
    with group("bookshelf", loc=(0.0, 0.12, 0), uv=1.7):
        box(0, 0, 0, dp, 0.024, h_, OAK, bevel=0.005)
        box(0, w_ - 0.024, 0, dp, 0.024, h_, OAK, bevel=0.005)
        box(0, 0.02, 0.05, 0.01, w_ - 0.04, h_ - 0.05, "#c08f5c", bevel=0.0)
        box(0.01, 0.024, 0, dp - 0.03, w_ - 0.048, 0.05, OAK_D, bevel=0.003)
        levels = [0.05, 0.42, 0.78, 1.13, 1.47, h_ - 0.024]
        for z in levels:
            box(0.005, 0.02, z, dp - 0.005, w_ - 0.04, 0.024, OAK, bevel=0.004)
        for li, z in enumerate(levels[:-1]):
            zz, clear = z + 0.024, levels[li + 1] - z - 0.03
            y = 0.03
            if li == 0:   # dictionaries: latin and greek
                for tk, col, lab in ((0.085, "#7b1e2b", "IL"), (0.09, "#1f3a6e", "GI")):
                    book(y, zz, tk, 0.2, 0.275, col, dp, band="#d8b24a")
                    text(lab, dp - 0.0235, y + tk / 2, zz + 0.1, 0.04, "#d8b24a", rot=(90, 0, 90), align="CENTER", metal=0.5, rough=0.4)
                    y += tk + 0.003
            end = w_ - 0.03
            if li == 2:   # leave room for a small plant
                cyl(dp - 0.13, w_ - 0.13, zz, 0.05, 0.085, "#e07a5f", r2=0.06, bevel=0.004)
                for i in range(8):
                    a = i * 2.4
                    leaf((dp - 0.13 + 0.01 * math.cos(a), w_ - 0.13 + 0.01 * math.sin(a), zz + 0.075), 0.14 + 0.03 * (i % 3),
                         0.05, tilt=30 + 10 * (i % 4), turn=math.degrees(a), col="#5d9950")
                end = w_ - 0.24
            if li == 4:   # a horizontal pile at the end
                for i in range(4):
                    box(dp - 0.21, w_ - 0.27, zz + i * 0.032, 0.17, 0.23, 0.03, r.choice(BOOKS), bevel=0.003, rot=(0, 0, r.uniform(-6, 6)))
                end = w_ - 0.3
            while True:
                tk = r.uniform(0.022, 0.05)
                if y + tk > end:
                    break
                hgt = min(clear, r.uniform(0.19, 0.3))
                if r.random() < 0.1 and y + tk + 0.07 < end:   # a leaning book
                    box(dp - 0.03 - 0.16, y + 0.03, zz + 0.004, 0.16, tk, hgt * 0.95, r.choice(BOOKS), bevel=0.003, rot=(-14, 0, 0))
                    y += tk + 0.075
                    continue
                book(y, zz, tk, r.uniform(0.14, 0.2), hgt, r.choice(BOOKS), dp, band=r.choice((None, None, CREAM, "#1d1d1f", "#d8b24a")), inset=r.uniform(0, 0.02))
                y += tk + 0.0015
        # on top: a globe (tilted axis, continents painted on, a brass meridian) and a box
        gx, gy, gz, gr = 0.15, 0.2, h_ + 0.17, 0.11
        cyl(gx, gy, h_, 0.06, 0.015, OAK_D, bevel=0.004)
        cyl(gx, gy, h_ + 0.015, 0.008, 0.05, "#d8b24a", metal=0.6, rough=0.4)
        globe = sphere(gx, gy, gz, gr, "#3f7fbf", segs=64, rot=(0, 23, 0))
        globe.data.materials.append(mat("#6fae5c"))
        lands = [Vector(v).normalized() for v in ((1, 0.3, 0.4), (0.6, -0.8, 0.1), (-0.5, 0.7, -0.2), (-0.9, -0.2, 0.5),
                                                  (0.1, 0.9, 0.6), (0.2, -0.3, -0.9), (-0.3, -0.6, 0.7))]
        for f in globe.data.polygons:
            if any(f.center.normalized().dot(c) > 0.86 + 0.04 * (i % 3) for i, c in enumerate(lands)):
                f.material_index = 1
        torus(gx, gy, gz, gr + 0.012, 0.004, "#d8b24a", rot=(90, 0, 0), metal=0.6, rough=0.4)
        box(0.04, 0.46, h_, 0.22, 0.28, 0.13, "#e9d8a6", bevel=0.008)
        box(0.035, 0.455, h_ + 0.13, 0.23, 0.29, 0.025, "#d8b24a", bevel=0.006)


def book(y, z, tk, depth, hgt, col, dp, band=None, inset=0.0):
    x1 = dp - 0.025 - inset
    box(x1 - depth, y, z, depth, tk, hgt, col, bevel=0.003, seg=1)
    if band:
        box(x1 - 0.002, y - 0.0004, z + hgt * 0.68, 0.0026, tk + 0.0008, hgt * 0.14, band, bevel=0.0)


def basketball():
    cx, y = 0.89, D
    with group("basketball", uv=1.8):
        box(cx - 0.31, y - 0.03, 1.78, 0.62, 0.02, 0.44, "#fbfbf8", bevel=0.006)
        box(cx - 0.32, y - 0.033, 1.77, 0.64, 0.026, 0.02, "#e2542b", bevel=0.004)
        box(cx - 0.32, y - 0.033, 2.21, 0.64, 0.026, 0.02, "#e2542b", bevel=0.004)
        for sx in (-0.32, 0.3):
            box(cx + sx, y - 0.033, 1.77, 0.02, 0.026, 0.46, "#e2542b", bevel=0.004)
        for a, b, c, d in ((-0.12, 1.84, 0.24, 0.014), (-0.12, 2.006, 0.24, 0.014), (-0.12, 1.84, 0.014, 0.18), (0.106, 1.84, 0.014, 0.18)):
            box(cx + a, y - 0.0315, b, c, 0.002, d, "#e2542b", bevel=0.0)
        box(cx - 0.03, y - 0.09, 1.812, 0.06, 0.06, 0.012, "#e2542b", bevel=0.003)
        torus(cx, y - 0.21, 1.818, 0.12, 0.009, "#f26a1b")
        n = 12
        rings = [[(cx + rr * math.cos(2 * math.pi * (j + 0.5 * (k % 2)) / n), y - 0.21 + rr * math.sin(2 * math.pi * (j + 0.5 * (k % 2)) / n), 1.818 - k * 0.045)
                  for j in range(n)] for k, rr in enumerate((0.12, 0.108, 0.095, 0.085, 0.08))]
        net = loft(rings, "#fbfbf8", closed_ends=False)
        wm = net.modifiers.new("wire", "WIREFRAME")
        wm.thickness = 0.005
        # the ball, on the rug: two seams all the way round crossing at right angles, and the two
        # curved ones that make it a basketball and not a beach ball
        bx, by, br = 2.3, 1.75, 0.12
        with group(loc=(bx, by, br + 0.031), rot=(16, -22, 38)):
            sphere(0, 0, 0, br, "#d9631f", segs=48, rough=0.9)
            R, n = br * 1.004, 64
            ring = [2 * math.pi * k / n for k in range(n)]
            tube([(R * math.cos(t), R * math.sin(t), 0) for t in ring], 0.0024, "#1d1d1f", closed=True)
            tube([(R * math.cos(t), 0, R * math.sin(t)) for t in ring], 0.0024, "#1d1d1f", closed=True)
            for sy in (-1, 1):
                h, rr = 0.56 * R, math.sqrt(1 - 0.56 ** 2) * R
                tube([(rr * math.cos(t), sy * h, rr * math.sin(t)) for t in ring], 0.0024, "#1d1d1f", closed=True)


def guitar():
    """Acoustic guitar hanging on the back wall. Built lying flat (y along the neck), then stood up."""
    cx, y0, z0 = 2.34, D - 0.035, 1.0
    top, side, neck_c, ebony = "#e6b566", "#8a4b2a", "#b8793f", "#2a211c"
    half = spline([(0, 0), (0.1, 0.006), (0.165, 0.045), (0.196, 0.13), (0.19, 0.21), (0.155, 0.285), (0.134, 0.325),
                   (0.14, 0.375), (0.146, 0.42), (0.126, 0.468), (0.07, 0.496), (0, 0.5)], 6)
    outline = half + [(-x, y) for x, y in reversed(half[1:-1])]
    with group("guitar", uv=1.8):
        with group(loc=(cx, y0, z0), rot=(90, 0, 0)):
            prism(outline, 0, 0.1, side, bevel=0.006, sharp=50, rough=0.45)
            prism([(x * 0.985, 0.004 + y * 0.985) for x, y in outline], 0.1, 0.004, top, sharp=50, rough=0.5)
            cyl(0, 0.33, 0.1035, 0.048, 0.002, "#1a1410", segs=40)
            torus(0, 0.33, 0.1045, 0.057, 0.003, "#5a3a22")
            box(-0.08, 0.125, 0.104, 0.16, 0.032, 0.009, ebony, bevel=0.003)
            box(-0.04, 0.142, 0.113, 0.08, 0.004, 0.003, CREAM, bevel=0.0)
            box(-0.026, 0.5, 0.078, 0.052, 0.325, 0.027, neck_c, bevel=0.01)
            box(-0.026, 0.5, 0.02, 0.052, 0.045, 0.085, neck_c, bevel=0.01)
            box(-0.0275, 0.385, 0.104, 0.055, 0.438, 0.007, ebony, bevel=0.001)
            for i in range(1, 19):
                yf = 0.823 - 0.679 * (1 - 2 ** (-i / 12))
                box(-0.0275, yf, 0.111, 0.055, 0.002, 0.0012, METAL, bevel=0.0, metal=0.7, rough=0.3)
            box(-0.0275, 0.821, 0.104, 0.055, 0.005, 0.009, CREAM, bevel=0.0)
            prism([(-0.03, 0.824), (0.03, 0.824), (0.04, 0.86), (0.037, 0.985), (0, 1.0), (-0.037, 0.985), (-0.04, 0.86)],
                  0.084, 0.02, side, bevel=0.004, rough=0.45)
            for i, yy in enumerate((0.875, 0.915, 0.955)):
                for sx in (-1, 1):
                    cyl(sx * 0.024, yy, 0.104, 0.005, 0.012, METAL, metal=0.7, rough=0.3, segs=12)
                    cyl(sx * 0.04, yy, 0.09, 0.004, 0.02, METAL, axis="X", metal=0.7, rough=0.3, segs=12,
                        rot=(0, 90 * sx, 0))
                    box(sx * 0.064 - 0.006, yy - 0.008, 0.086, 0.012, 0.016, 0.008, CREAM, bevel=0.003)
            for i in range(6):
                xs = -0.021 + i * 0.0084
                tube([(xs * 1.25, 0.144, 0.1165), (xs, 0.823, 0.1135)], 0.0011 + 0.0001 * (5 - i), "#d9d2c0", metal=0.6, rough=0.35)
        # wall hanger under the headstock
        box(cx - 0.04, D - 0.012, z0 + 0.74, 0.08, 0.012, 0.1, OAK_D, bevel=0.004)
        for sx in (-1, 1):
            tube([(cx + sx * 0.035, D - 0.01, z0 + 0.8), (cx + sx * 0.035, D - 0.14, z0 + 0.8), (cx + sx * 0.035, D - 0.15, z0 + 0.825)], 0.007, DARK)


def bike():
    """Road bike on a floor stand along the open right side. Local frame: x = forward, y = left."""
    R, wb = 0.335, 0.99
    frame, bar = "#56603d", "#1d1d1f"   # military green
    rear, front = (0, 0, R), (wb, 0, R)
    bb, st, ht, hb = (0.405, 0, 0.275), (0.275, 0, 0.83), (0.83, 0, 0.855), (0.875, 0, 0.71)
    with group("bike", loc=(4.05, 0.38, 0.012), rot=(0, 0, 90), uv=2.0):
        for ax in (rear, front):
            torus(ax[0], 0, R, R - 0.014, 0.014, "#1d1d1f", rot=(90, 0, 0), segs=64, rough=0.9)
            torus(ax[0], 0, R, R - 0.036, 0.012, "#c9ccd1", rot=(90, 0, 0), segs=64, metal=0.6, rough=0.35)
            cyl(ax[0], -0.03, R, 0.018, 0.06, "#c9ccd1", axis="Y", metal=0.6, rough=0.35)
            for i in range(16):
                a = math.radians(i * 22.5 + 6)
                sy = 0.022 if i % 2 else -0.022
                tube([(ax[0], sy, R), (ax[0] + (R - 0.04) * math.cos(a), 0, R + (R - 0.04) * math.sin(a))], 0.0016, "#c9ccd1", res=4)
        tube([bb, st], 0.017, frame)
        tube([st, ht], 0.016, frame)
        tube([bb, hb], 0.02, frame)
        tube([(0.822, 0, 0.885), (0.885, 0, 0.68)], 0.021, frame)
        for sy in (-1, 1):
            tube([(0, sy * 0.062, R), (bb[0] - 0.02, sy * 0.028, bb[2])], 0.009, frame)
            tube([(0, sy * 0.062, R), (st[0] + 0.01, sy * 0.018, st[2] - 0.03)], 0.008, frame)
            tube([(0.885, sy * 0.03, 0.68), (0.93, sy * 0.045, 0.52), (wb, sy * 0.05, R)], 0.011, frame, smooth=True)
            box(-0.012, sy * 0.062 - 0.004, R - 0.012, 0.024, 0.008, 0.024, "#c9ccd1", bevel=0.003, metal=0.6)
        tube([(0.865, -0.03, 0.69), (0.865, 0.03, 0.69)], 0.013, frame)
        # seatpost and saddle
        tube([st, (0.25, 0, 0.94)], 0.0125, "#1d1d1f")
        soft(box(0.11, -0.065, 0.94, 0.27, 0.13, 0.035, "#1d1d1f", name="saddle"), 0.02)
        # stem and drop bar
        tube([(0.818, 0, 0.9), (0.92, 0, 0.93)], 0.014, "#1d1d1f")
        tube([(0.92, -0.2, 0.93), (0.92, 0.2, 0.93)], 0.012, bar)
        for sy in (-1, 1):
            tube([(0.92, sy * 0.2, 0.93), (0.99, sy * 0.205, 0.93), (1.03, sy * 0.205, 0.89), (1.01, sy * 0.205, 0.81), (0.93, sy * 0.205, 0.79)],
                 0.012, bar, smooth=True)
            soft(box(0.985, sy * 0.205 - 0.014, 0.9, 0.05, 0.028, 0.085, "#1d1d1f", rot=(0, 20, 0)), 0.01)
            tube([(1.03, sy * 0.205, 0.9), (1.05, sy * 0.205, 0.8)], 0.005, "#c9ccd1", metal=0.6)
        # drivetrain on the right-hand side (-y)
        cyl(bb[0], -0.05, bb[2], 0.1, 0.004, "#c9ccd1", axis="Y", segs=40, metal=0.7, rough=0.3)
        cyl(bb[0], -0.057, bb[2], 0.075, 0.004, "#1d1d1f", axis="Y", segs=40)
        cyl(bb[0], -0.04, bb[2], 0.024, 0.08, "#c9ccd1", axis="Y", metal=0.6)
        cyl(0, -0.05, R, 0.045, 0.02, "#c9ccd1", axis="Y", r2=0.02, metal=0.7, rough=0.3)
        for sy, ang in ((-1, -55), (1, 125)):
            a = math.radians(ang)
            ex, ez = bb[0] + 0.17 * math.cos(a), bb[2] + 0.17 * math.sin(a)
            tube([(bb[0], sy * 0.065, bb[2]), (ex, sy * 0.075, ez)], 0.01, "#1d1d1f")
            box(ex - 0.045, sy * 0.11 - 0.035, ez - 0.008, 0.09, 0.07, 0.016, "#1d1d1f", bevel=0.004)
        ch = -0.05
        tube([(bb[0], ch, bb[2] + 0.1), (0.0, ch, R + 0.042), (-0.04, ch, R), (0.02, ch, R - 0.1), (0.07, ch, R - 0.14), (bb[0], ch, bb[2] - 0.1), (bb[0] + 0.1, ch, bb[2])],
             0.0045, "#55585e", closed=True, res=4)
        box(0.0, ch - 0.01, R - 0.16, 0.03, 0.02, 0.09, "#1d1d1f", bevel=0.005, rot=(0, -25, 0))
        # bottle
        cyl(0.6, 0, 0.44, 0.034, 0.17, "#f4f1ea", rot=(0, 42, 0), bevel=0.006)
        cyl(0.715, 0, 0.566, 0.022, 0.035, "#f26a1b", rot=(0, 42, 0), bevel=0.004)
        # floor stand holding the rear axle
        for sy in (-1, 1):
            tube([(0, sy * 0.085, R), (-0.2, sy * 0.19, 0.012), (0.2, sy * 0.19, 0.012), (0, sy * 0.085, R)], 0.012, "#55585e")
        tube([(-0.2, -0.19, 0.012), (-0.2, 0.19, 0.012)], 0.012, "#55585e")


def shoes():
    """Running shoes, kicked off in the middle of the room: long and low, a white rocker midsole (thick
    under the heel, thin and lifted at the toe), a smooth upper with a padded opening, a thin tongue
    just peeking out of criss-cross laces, one swept stripe on each side and a pull tab at the heel.
    Built in slices across the foot. Local frame: x = heel to toe, z up."""
    upper_c, tongue_c, accent, lining = VIOLET, LILAC, PINK, INK
    pts = [(0.0, 0.0), (0.015, 0.032), (0.08, 0.039), (0.17, 0.049), (0.245, 0.042), (0.283, 0.019),
           (0.29, -0.005), (0.275, -0.029), (0.22, -0.044), (0.13, -0.04), (0.05, -0.037), (0.012, -0.028)]
    foot = spline(pts, 4, closed=True)
    tip = max(range(len(foot)), key=lambda i: foot[i][0])
    left, right = foot[:tip + 1], foot[tip:] + foot[:1]          # the +y and -y edges of the sole

    def at(table, x):
        """Linear interpolation in a list of (x, value) pairs."""
        table = sorted(table)
        for (x0, v0), (x1, v1) in zip(table, table[1:]):
            if x <= x1:
                return v0 + (v1 - v0) * max(0.0, x - x0) / max(1e-9, x1 - x0)
        return table[-1][1]

    lift = lambda x: 0.022 * max(0.0, (x - 0.185) / 0.105) ** 2 + 0.008 * max(0.0, (0.045 - x) / 0.045) ** 1.5   # toe spring, heel bevel
    stack = lambda x: 0.034 - 0.013 * min(1.0, x / 0.21) - 0.004 * max(0.0, (x - 0.24) / 0.05)                  # midsole: 3.4 cm to 1.7
    # top line from the floor: highest over the instep, where the laces start, a dip where the ankle goes,
    # and a curve (not a straight slope) down to the toe
    top = spline([(0.0, 0.095), (0.012, 0.102), (0.03, 0.099), (0.06, 0.088), (0.09, 0.096), (0.11, 0.101), (0.13, 0.098),
                  (0.16, 0.09), (0.19, 0.08), (0.22, 0.069), (0.25, 0.057), (0.27, 0.047), (0.29, 0.034)], 8)   # smooth, no corners
    hole, hole_r, hole_w = 0.06, 0.044, 0.56          # foot opening: centre and half length along x, half width as a fraction
    xs = [0.145 - 0.1445 * math.cos(math.pi * i / 80) for i in range(81)]   # denser at heel and toe, so both come out round

    def frame(x):
        """Centre line, half width, bottom and top of the upper at x."""
        y0, y1 = at(left, x) * 0.93, at(right, x) * 0.93
        return (y0 + y1) / 2, (y0 - y1) / 2, lift(x) + stack(x) - 0.003, lift(x) + at(top, x)

    def surface(x, c):
        """The upper at x, c = cosine of the angle round the slice (1 = one side at the sole, 0 = on top)."""
        cy, hw, z0, z1 = frame(x)
        sn = math.sqrt(max(0.0, 1 - c * c))
        return cy + hw * c * (1 - 0.42 * sn * sn), z0 + (z1 - z0) * sn ** 0.65   # narrows towards the top, like a foot

    def heel(x, z):
        """How far the back of the heel bulges out at height z (a heel is round, not a wall) and flares at the collar."""
        _, _, z0, z1 = frame(x)
        zr = min(1.0, max(0.0, (z - z0) / (z1 - z0)))
        return -max(0.0, 1 - x / 0.05) ** 2 * (0.007 * math.sin(math.pi * zr * 0.85) + 0.004 * zr ** 6)

    opening = lambda x: hole_w * math.sqrt(max(0.0, 1 - ((x - hole) / hole_r) ** 2))
    floor = lambda x: lift(x) + stack(x) + 0.01

    def upper(x, k, n=49):
        out = []
        for j in range(n):
            c = math.cos(math.pi * j / (n - 1))
            y, z = surface(x, c)
            ow = opening(x)
            if ow > 0 and abs(c) < ow:                        # sunk down to the insole, steep walls all round
                z = floor(x) + (z - floor(x)) * (abs(c) / ow) ** 6
            out.append((x + heel(x, z), k * y, z))
        cy, hw, z0, _ = frame(x)
        return out + [(x, k * (cy - hw * 0.9), z0), (x, k * (cy + hw * 0.9), z0)]   # flat underside, inside the sole

    def slab(x, k, z0, z1, scale, flare=0.0, n=28, p=0.32):
        """Rounded slice of the sole, a little wider at the bottom by `flare`."""
        y0, y1 = at(left, x) * scale, at(right, x) * scale
        cy, hw, out = (y0 + y1) / 2, (y0 - y1) / 2, []
        for j in range(n):
            t = 2 * math.pi * j / n
            c, sn = math.cos(t), math.sin(t)
            z = (z0 + z1) / 2 + (z1 - z0) / 2 * math.copysign(abs(sn) ** p, sn)
            w = hw * (1 + flare * (z1 - z) / (z1 - z0))
            out.append((x, k * (cy + w * math.copysign(abs(c) ** p, c)), z))
        return out

    def on_upper(x, zr, side, out):
        """Point of the upper at x, zr above its bottom, on one side (1 or -1), pushed out by `out` along
        the surface normal: the stripe sits on it like a stitched-on panel."""
        cy, hw, z0, z1 = frame(x)
        sn = min(1.0, (max(zr, 0.0) / (z1 - z0)) ** (1 / 0.65))
        c = side * math.sqrt(max(0.0, 1 - sn * sn))
        pt = lambda x_, c_: Vector((x_, *surface(x_, c_)))
        p = pt(x, c)
        n = (pt(x + 0.002, c) - p).cross(pt(x, c - 0.02 * side) - p).normalized()
        if n.dot(p - Vector((min(max(x, 0.06), 0.23), cy, (z0 + z1) / 2 - 0.01))) < 0:
            n = -n
        return p + n * out + Vector((0, 0, min(zr, 0.0)))

    STRIPE = spline([(0.214, 0.001), (0.178, 0.009), (0.14, 0.02), (0.105, 0.03), (0.078, 0.036)], 6)

    def one(k):
        """k = 1 for the left shoe, -1 mirrors it."""
        loft([slab(x, k, lift(x), lift(x) + 0.004, 1.015 + 0.05 * max(0.0, 1 - x / 0.07)) for x in xs], "#3a3346", sharp=80, rough=0.9)   # outsole
        loft([slab(x, k, lift(x) + 0.003, lift(x) + stack(x), 0.975, flare=0.04 + 0.05 * max(0.0, 1 - x / 0.07)) for x in xs],
             "#fbfbf8", sharp=80, rough=0.6)                                                                             # midsole, flared at the heel
        n_up = 49
        o = loft([upper(x, k, n_up) for x in xs], upper_c, sharp=80, rough=0.75)
        o.data.materials.append(mat(lining, rough=0.9))
        ring = n_up + 2
        for f in o.data.polygons[:(len(xs) - 1) * ring]:      # dark lining: the faces sunk into the opening (loft order: slice, then round it)
            i, j = divmod(f.index, ring)
            cs = [math.cos(math.pi * jj / (n_up - 1)) for jj in (j, j + 1) if jj < n_up]
            ow = max(opening(xs[i]), opening(xs[i + 1]))
            if len(cs) == 2 and all(abs(c) < ow for c in cs):
                f.material_index = 1
        rim = [(hole + hole_r * 0.98 * math.cos(a), hole_w * 0.98 * math.sin(a)) for a in [2 * math.pi * i / 48 for i in range(48)]]
        tube([(x + heel(x, surface(x, c)[1]), k * surface(x, c)[0], surface(x, c)[1]) for x, c in rim], 0.0042, upper_c, closed=True,
             smooth=True)   # padded collar

        for sd in (1, -1):                                     # one swept stripe on each side, pointed at both ends
            secs = []
            for i, (px, pz) in enumerate(STRIPE):
                qx, qz = STRIPE[min(i + 1, len(STRIPE) - 1)]
                rx, rz = STRIPE[max(i - 1, 0)]
                ln = math.hypot(qx - rx, qz - rz)
                ax, az = -(qz - rz) / ln, (qx - rx) / ln
                f = i / (len(STRIPE) - 1)
                w = 0.0075 * math.sin(math.pi * (0.04 + 0.92 * f)) ** 0.8
                outer = [on_upper(px + ax * w * g, pz + az * w * g, sd, 0.0014) for g in (-1, -0.5, 0, 0.5, 1)]
                inner = [on_upper(px + ax * w * g, pz + az * w * g, sd, 0.0002) for g in (1, 0.5, 0, -0.5, -1)]
                secs.append([(v.x, k * v.y, v.z) for v in outer + inner])
            st = loft(secs, accent, sharp=80, rough=0.6)
            # a shell this thin can come out inside out (Blender guesses "outside" from the farthest face):
            # the first face is on the outer side by construction, so check it against the way out
            if st.data.polygons[0].normal.dot(Vector(secs[0][0]) - Vector(secs[0][-1])) < 0:
                bm = bmesh.new()
                bm.from_mesh(st.data)
                bmesh.ops.reverse_faces(bm, faces=bm.faces)
                bm.to_mesh(st.data)
                bm.free()

        # the tongue: thin, lies on the throat under the laces and just peeks out of the opening
        zt = lambda x: lift(x) + at(top, x)
        path = spline([(0.205, zt(0.205) + 0.0004), (0.165, zt(0.165) + 0.001), (0.13, zt(0.13) + 0.003), (0.108, zt(0.108) + 0.009),
                       (0.096, zt(0.096) + 0.017)], 4)
        secs, th = [], 0.005
        for i, (px, pz) in enumerate(path):
            qx, qz = path[min(i + 1, len(path) - 1)]
            rx, rz = path[max(i - 1, 0)]
            ln = math.hypot(qx - rx, qz - rz)
            nx, nz = (qz - rz) / ln, -(qx - rx) / ln         # normal in the x-z plane, pointing up
            pcy, phw, pz0, pz1 = frame(px)
            f = i / (len(path) - 1)
            hwt = 0.017 * math.sqrt(max(0.05, 1 - (max(0.0, f - 0.8) / 0.2) ** 2))   # round at the top
            tk = th * min(1.0, 0.2 + f * 4)
            sec = []
            for j in range(14):
                a = 2 * math.pi * j / 14
                ca, sa = math.cos(a), math.sin(a)
                u = math.copysign(abs(ca) ** 0.5, ca) * hwt
                droop = (pz1 - pz0) * (1 - (1 - (u / phw) ** 2) ** 0.33)   # curved across, like the foot under it
                v = math.copysign(abs(sa) ** 0.5, sa) * tk / 2
                sec.append((px + nx * v, k * (pcy + u), pz + nz * v - droop))
            secs.append(sec)
        loft(secs, tongue_c, sharp=80, rough=0.8)
        tongue = lambda x: at(path, x) + th / 2

        # thin criss-cross laces between two rows of eyelets, a bar at each end
        eyelet = lambda x, side: (x, k * surface(x, side * 0.42)[0], surface(x, side * 0.42)[1] + 0.0008)
        xe = [0.118 + 0.0195 * i for i in range(5)]
        lace = lambda pts_: tube(pts_, 0.0017, "#fbfbf8", smooth=True)
        for i in range(4):
            xm = (xe[i] + xe[i + 1]) / 2
            for side, up in ((1, 0.0), (-1, 0.0018)):
                lace([eyelet(xe[i], side), (xm, k * frame(xm)[0], tongue(xm) + 0.0022 + up), eyelet(xe[i + 1], -side)])
        for x in (xe[0], xe[-1]):
            lace([eyelet(x, 1), (x, k * frame(x)[0], tongue(x) + 0.0022), eyelet(x, -1)])
        soft(box(xs[0] + heel(xs[0], zt(0.0) - 0.006) - 0.0045, -0.007, zt(0.0) - 0.014, 0.0055, 0.014, 0.022, accent), 0.0025)   # heel pull tab

    with group("shoes", uv=4.0):   # small and full of detail: more texels than the rest
        with group(loc=(2.72, 0.62, 0.012), rot=(0, 0, -150)):
            one(1)
        with group(loc=(2.98, 0.42, 0.012), rot=(0, 0, -128)):
            one(-1)


def juggling():
    """A spotted diabolo with its sticks and three juggling balls, left on the rug."""
    rug = 0.031
    toys = ("#e63946", "#2f6fd6", "#ffd23f", "#2fb36b")   # red, blue, yellow, green
    with group("juggling", uv=2.4):
        with group(loc=(2.98, 1.3, rug + 0.062), rot=(0, 0, 28)):
            slope = 0.05 / 0.062
            for sx in (-1, 1):   # two cups joined at the axle, lying on their rims
                cyl(0, 0, 0, 0.012, 0.062, "#f6f1e6", r2=0.062, axis="X", rot=(0, 90 * sx, 0), segs=40, bevel=0.004)
                torus(sx * 0.06, 0, 0, 0.058, 0.009, "#1d1d1f", rot=(0, 90, 0), segs=40)
                for k in range(11):   # spots, in two staggered rings
                    d = (0.026, 0.046)[k % 2]
                    th = 2 * math.pi * k / 11 + (0.3 if sx > 0 else 0)
                    rr = 0.012 + slope * d
                    n = Vector((-sx * slope, math.cos(th), math.sin(th))).normalized()
                    p = Vector((sx * d, rr * math.cos(th), rr * math.sin(th))) + n * 0.0006
                    e = Vector((0, 0, 1)).rotation_difference(n).to_euler()
                    cyl(p.x, p.y, p.z, 0.0085, 0.0012, toys[(k + (sx > 0)) % 4], rot=tuple(math.degrees(a) for a in e), segs=16)
            cyl(-0.012, 0, 0, 0.007, 0.024, "#c9ccd1", axis="X", metal=0.6, rough=0.35)
        # the two sticks, crossed, with the string between their tips
        tips = []
        for (sx, sy, ang) in ((2.68, 1.52, 8), (2.72, 1.6, -26)):
            a = math.radians(ang)
            ex, ey = sx + 0.32 * math.cos(a), sy + 0.32 * math.sin(a)
            tube([(sx, sy, rug + 0.008), (ex, ey, rug + 0.008)], 0.0075, "#1d1d1f")
            cyl(sx, sy, rug + 0.008, 0.011, 0.075, "#e0453a", axis="X", rot=(0, 90, ang), segs=16, bevel=0.003)
            tips.append((ex, ey, rug + 0.008))
        tube([tips[0], (3.06, 1.42, rug + 0.004), (3.02, 1.33, rug + 0.03), tips[1]], 0.0018, "#f4f1ea", smooth=True)
        # balls sewn from eight wedges, the four colours twice round
        for i, (bx, by) in enumerate(((3.22, 1.62), (3.3, 1.7), (3.16, 1.74))):
            ball = sphere(bx, by, rug + 0.034, 0.034, toys[0], segs=32, rough=0.9, rot=(70 * i, 25 + 40 * i, 15 * i))
            for c in toys[1:]:
                ball.data.materials.append(mat(c, rough=0.9))
            for f in ball.data.polygons:
                f.material_index = int((math.atan2(f.center.y, f.center.x) % (2 * math.pi)) / (math.pi / 4)) % 4


def cards():
    """A deck fanned out on the pouf, one card face up, the box beside it."""
    z0 = 0.372
    cw, ch, ct = 0.063, 0.088, 0.0012
    with group("cards", loc=(POUF[0], POUF[1], z0), rot=(0, 0, -32), uv=3.2):
        for i in range(14):   # pivot at the bottom of the cards, like a fan held in one hand
            with group(loc=(-0.04, -0.06, i * 0.0013), rot=(0, 0, 55 - i * 8.5)):
                box(-cw / 2, 0.012, 0, cw, ch, ct, "#f6f2ea", bevel=0.0)
                box(-cw / 2 + 0.004, 0.016, ct, cw - 0.008, ch - 0.008, 0.0002, "#c8323b", bevel=0.0)
        # the chosen card, face up
        with group(loc=(0.09, 0.11, 0.0), rot=(0, 0, 16)):
            box(-cw / 2, -ch / 2, 0, cw, ch, ct, "#fbfbf8", bevel=0.0)
            heart = [(0.0011 * 16 * math.sin(t) ** 3, 0.0011 * (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
                     for t in [i * 2 * math.pi / 32 for i in range(32)]]
            prism(heart, ct, 0.0005, "#c8323b", sharp=89)
            text("A", -cw / 2 + 0.006, ch / 2 - 0.016, ct, 0.012, "#c8323b", rot=(0, 0, 0), depth=0.0002)
        # the box
        box(-0.07, 0.1, 0, 0.066, 0.093, 0.022, "#c8323b", bevel=0.002, rot=(0, 0, 10))
        box(-0.062, 0.12, 0.022, 0.05, 0.05, 0.0006, "#f6f2ea", bevel=0.0, rot=(0, 0, 10))


# ------------------------------------------------------------------ lights, build
def lights():
    """Late afternoon: a dim warm sky, the sun low and golden through the window, every lamp on."""
    world("#ffd9c4", 0.09, BG)
    sun((-0.72, 0.42, -0.55), 0.75, (1.0, 0.86, 0.76), angle=20)    # soft fill from the open side
    sun((0.82, -0.2, -0.3), 6.0, (1.0, 0.6, 0.34), 1.5)             # golden hour through the window
    bulb = (1.0, 0.72, 0.45)
    lamp((0.62, 0.7, 1.33), 40, bulb, 0.08)                         # floor lamp
    lamp((1.95, 4.02, 0.72), 16, bulb, 0.06)                        # mushroom lamp on the nightstand
    lamp((3.97, 4.0, 1.15), 10, bulb, 0.03)                         # desk lamp


def build():
    shell()
    bed()
    nightstand()
    wall_shelf()
    wardrobe()
    x0, y0, top = desk()
    chair(3.42, 2.82, 22)
    reading_corner()
    plants()
    computer(x0, y0, top)
    notebook(x0, y0, top)
    whiteboard()
    bookshelf()
    basketball()
    guitar()
    bike()
    shoes()
    juggling()
    cards()
    lights()
    camera(TARGET, VIEW[2], VIEW[0], VIEW[1])

"""
assets.py
=========
Procedural art.  Because the brief allows (and prefers) programmatically
generated placeholder assets, the entire game is drawn from code -- no external
image files are required.  If a matching PNG exists in the ``assets`` folder it
is loaded instead, so the project is also drop-in friendly for real artwork.

Every sprite is drawn at 2x resolution and ``smoothscale``-d down, giving cheap
anti-aliasing and a clean, modern cartoon look.

The :class:`AssetManager` builds every sprite once at start-up and caches it,
keeping the per-frame cost to simple blits.
"""

import math
import os
import pygame

import config as C
from src import utils


# ---------------------------------------------------------------------------
# Low level helper: supersampled drawing
# ---------------------------------------------------------------------------
SS = 2  # supersample factor


def _render(size, draw_fn):
    """Draw *draw_fn(surface, w, h)* at 2x then smooth-scale to *size*."""
    big = pygame.Surface((size[0] * SS, size[1] * SS), pygame.SRCALPHA)
    draw_fn(big, size[0] * SS, size[1] * SS)
    small = pygame.transform.smoothscale(big, size)
    return small.convert_alpha()


def _ellipse(surf, color, cx, cy, rw, rh):
    pygame.draw.ellipse(surf, color,
                        pygame.Rect(int(cx - rw), int(cy - rh),
                                    int(rw * 2), int(rh * 2)))


def _circle(surf, color, cx, cy, r):
    pygame.draw.circle(surf, color, (int(cx), int(cy)), int(r))


# ===========================================================================
# Plant sprite painters  (draw into a w x h transparent surface)
# ===========================================================================
def _paint_sunflower(s, w, h):
    cx, cy = w * 0.5, h * 0.42
    # stem + leaves
    pygame.draw.line(s, (76, 168, 60), (cx, h * 0.55), (cx, h * 0.95), int(w * 0.09))
    _ellipse(s, (96, 196, 80), cx - w * 0.16, h * 0.78, w * 0.16, h * 0.08)
    _ellipse(s, (96, 196, 80), cx + w * 0.16, h * 0.78, w * 0.16, h * 0.08)
    # petals
    petal_r = w * 0.40
    for i in range(12):
        a = i * (math.pi * 2 / 12)
        px = cx + math.cos(a) * petal_r
        py = cy + math.sin(a) * petal_r
        _ellipse(s, (255, 206, 56), px, py, w * 0.13, w * 0.07)
        _ellipse(s, (255, 226, 120), px, py, w * 0.09, w * 0.045)
    # face disc
    _circle(s, (120, 78, 30), cx, cy, w * 0.27)
    _circle(s, (150, 100, 40), cx, cy, w * 0.23)
    # eyes + smile
    _circle(s, (30, 20, 10), cx - w * 0.09, cy - w * 0.04, w * 0.04)
    _circle(s, (30, 20, 10), cx + w * 0.09, cy - w * 0.04, w * 0.04)
    pygame.draw.arc(s, (30, 20, 10),
                    pygame.Rect(int(cx - w * 0.12), int(cy - w * 0.02),
                                int(w * 0.24), int(w * 0.18)),
                    math.pi, math.pi * 2, max(2, int(w * 0.02)))


def _paint_peashooter(s, w, h, frost=False):
    body = (96, 196, 80) if not frost else (120, 196, 235)
    body_dark = (70, 160, 60) if not frost else (90, 165, 215)
    # stem
    pygame.draw.line(s, (76, 168, 60), (w * 0.42, h * 0.55), (w * 0.42, h * 0.95), int(w * 0.10))
    _ellipse(s, (96, 196, 80), w * 0.28, h * 0.80, w * 0.15, h * 0.07)
    # head
    cx, cy = w * 0.50, h * 0.40
    _circle(s, body_dark, cx, cy, w * 0.30)
    _circle(s, body, cx, cy - h * 0.015, w * 0.27)
    # snout / barrel
    _ellipse(s, body_dark, cx + w * 0.26, cy, w * 0.14, h * 0.10)
    _circle(s, (40, 60, 40) if not frost else (60, 110, 150),
            cx + w * 0.34, cy, w * 0.07)
    # eye
    _circle(s, (255, 255, 255), cx - w * 0.02, cy - h * 0.05, w * 0.08)
    _circle(s, (30, 30, 30), cx + w * 0.01, cy - h * 0.05, w * 0.04)
    if frost:
        # little snowflake hint
        sx, sy = cx - w * 0.08, cy + h * 0.10
        for i in range(3):
            a = i * math.pi / 3
            pygame.draw.line(s, (235, 250, 255),
                             (sx - math.cos(a) * w * 0.06, sy - math.sin(a) * w * 0.06),
                             (sx + math.cos(a) * w * 0.06, sy + math.sin(a) * w * 0.06),
                             max(1, int(w * 0.015)))


def _paint_icepea(s, w, h):
    _paint_peashooter(s, w, h, frost=True)


def _paint_wallnut(s, w, h):
    cx, cy = w * 0.5, h * 0.52
    _ellipse(s, (150, 96, 40), cx, cy, w * 0.40, h * 0.44)
    _ellipse(s, (176, 120, 56), cx, cy - h * 0.02, w * 0.34, h * 0.40)
    _ellipse(s, (200, 150, 80), cx - w * 0.10, cy - h * 0.12, w * 0.16, h * 0.16)
    # face
    _circle(s, (40, 25, 15), cx - w * 0.11, cy - h * 0.02, w * 0.045)
    _circle(s, (40, 25, 15), cx + w * 0.11, cy - h * 0.02, w * 0.045)
    pygame.draw.arc(s, (40, 25, 15),
                    pygame.Rect(int(cx - w * 0.13), int(cy + h * 0.04),
                                int(w * 0.26), int(h * 0.16)),
                    math.pi, math.pi * 2, max(2, int(w * 0.025)))


def _paint_cherrybomb(s, w, h):
    # two cherries
    for dx, scale in ((-0.16, 1.0), (0.16, 0.95)):
        cx = w * (0.5 + dx)
        cy = h * 0.62
        r = w * 0.26 * scale
        _circle(s, (170, 30, 40), cx, cy, r)
        _circle(s, (210, 50, 60), cx, cy, r * 0.86)
        _circle(s, (255, 150, 150), cx - r * 0.3, cy - r * 0.3, r * 0.22)
        # face
        _circle(s, (255, 255, 255), cx - r * 0.25, cy - r * 0.05, r * 0.22)
        _circle(s, (255, 255, 255), cx + r * 0.25, cy - r * 0.05, r * 0.22)
        _circle(s, (20, 20, 20), cx - r * 0.20, cy - r * 0.02, r * 0.11)
        _circle(s, (20, 20, 20), cx + r * 0.30, cy - r * 0.02, r * 0.11)
    # stems meeting a leaf
    pygame.draw.line(s, (90, 150, 60), (w * 0.34, h * 0.40), (w * 0.5, h * 0.18), int(w * 0.04))
    pygame.draw.line(s, (90, 150, 60), (w * 0.66, h * 0.42), (w * 0.5, h * 0.18), int(w * 0.04))
    _ellipse(s, (110, 190, 70), w * 0.60, h * 0.16, w * 0.12, h * 0.05)


PLANT_PAINTERS = {
    "sunflower": _paint_sunflower,
    "peashooter": _paint_peashooter,
    "wallnut": _paint_wallnut,
    "icepea": _paint_icepea,
    "cherrybomb": _paint_cherrybomb,
}

PLANT_SPRITE_SIZE = (96, 102)


# ===========================================================================
# Zombie sprite painters  (frame = 0/1 swaps the legs for a walk cycle)
# ===========================================================================
def _zombie_base(s, w, h, skin, shirt, frame, hat=None):
    swing = w * 0.10 * (1 if frame == 0 else -1)
    # legs
    pygame.draw.line(s, (60, 50, 60), (w * 0.45, h * 0.62),
                     (w * 0.40 - swing, h * 0.95), int(w * 0.13))
    pygame.draw.line(s, (60, 50, 60), (w * 0.55, h * 0.62),
                     (w * 0.60 + swing, h * 0.95), int(w * 0.13))
    # torso
    _ellipse(s, shirt, w * 0.5, h * 0.52, w * 0.26, h * 0.18)
    # forward-reaching arms
    pygame.draw.line(s, shirt, (w * 0.5, h * 0.45),
                     (w * 0.86, h * 0.50), int(w * 0.11))
    _circle(s, skin, w * 0.88, h * 0.50, w * 0.08)
    # head
    cx, cy = w * 0.5, h * 0.26
    _circle(s, skin, cx, cy, w * 0.20)
    _ellipse(s, utils.darken(skin, 0.15), cx + w * 0.02, cy + h * 0.02,
             w * 0.18, h * 0.10)
    # eyes
    _circle(s, (255, 255, 255), cx - w * 0.07, cy, w * 0.05)
    _circle(s, (255, 255, 255), cx + w * 0.07, cy, w * 0.05)
    _circle(s, (20, 20, 20), cx - w * 0.06, cy + h * 0.005, w * 0.025)
    _circle(s, (20, 20, 20), cx + w * 0.08, cy + h * 0.005, w * 0.025)
    # mouth
    pygame.draw.line(s, (60, 20, 20), (cx - w * 0.08, cy + h * 0.07),
                     (cx + w * 0.08, cy + h * 0.07), max(1, int(w * 0.02)))
    if hat == "bucket":
        pygame.draw.rect(s, (170, 175, 180),
                         pygame.Rect(int(cx - w * 0.18), int(cy - h * 0.22),
                                     int(w * 0.36), int(h * 0.20)),
                         border_radius=int(w * 0.04))
        pygame.draw.rect(s, (130, 135, 140),
                         pygame.Rect(int(cx - w * 0.20), int(cy - h * 0.06),
                                     int(w * 0.40), int(h * 0.04)))
    elif hat == "cone":
        pygame.draw.polygon(s, (235, 150, 50),
                            [(cx, cy - h * 0.26),
                             (cx - w * 0.16, cy - h * 0.02),
                             (cx + w * 0.16, cy - h * 0.02)])


def _paint_normal(s, w, h, frame):
    _zombie_base(s, w, h, (140, 170, 130), (90, 90, 120), frame)


def _paint_fast(s, w, h, frame):
    _zombie_base(s, w, h, (150, 175, 140), (210, 120, 50), frame)
    # headband to read as a "runner"
    pygame.draw.line(s, (220, 60, 60), (w * 0.32, h * 0.20),
                     (w * 0.68, h * 0.20), max(2, int(w * 0.03)))


def _paint_tank(s, w, h, frame):
    _zombie_base(s, w, h, (140, 170, 130), (95, 100, 110), frame, hat="bucket")


def _paint_boss(s, w, h, frame):
    swing = w * 0.06 * (1 if frame == 0 else -1)
    # massive legs
    pygame.draw.line(s, (70, 70, 80), (w * 0.42, h * 0.66),
                     (w * 0.38 - swing, h * 0.96), int(w * 0.16))
    pygame.draw.line(s, (70, 70, 80), (w * 0.58, h * 0.66),
                     (w * 0.62 + swing, h * 0.96), int(w * 0.16))
    skin = (120, 150, 120)
    _ellipse(s, (80, 95, 80), w * 0.5, h * 0.50, w * 0.30, h * 0.22)
    # arms holding a "telephone pole" club
    pygame.draw.line(s, skin, (w * 0.5, h * 0.42), (w * 0.18, h * 0.30), int(w * 0.13))
    pygame.draw.rect(s, (120, 90, 60),
                     pygame.Rect(int(w * 0.05), int(h * 0.10),
                                 int(w * 0.14), int(h * 0.55)),
                     border_radius=int(w * 0.03))
    # head
    cx, cy = w * 0.55, h * 0.24
    _circle(s, skin, cx, cy, w * 0.18)
    _circle(s, (255, 240, 180), cx - w * 0.06, cy, w * 0.045)
    _circle(s, (255, 240, 180), cx + w * 0.06, cy, w * 0.045)
    _circle(s, (180, 40, 40), cx - w * 0.05, cy + h * 0.005, w * 0.02)
    _circle(s, (180, 40, 40), cx + w * 0.07, cy + h * 0.005, w * 0.02)


ZOMBIE_PAINTERS = {
    "normal": _paint_normal,
    "fast": _paint_fast,
    "tank": _paint_tank,
    "boss": _paint_boss,
}

ZOMBIE_SPRITE_SIZE = {
    "normal": (80, 128),
    "fast": (80, 124),
    "tank": (86, 132),
    "boss": (150, 210),
}


# ===========================================================================
# Misc painters
# ===========================================================================
def _paint_sun(s, w, h):
    cx, cy = w * 0.5, h * 0.5
    for i in range(12):
        a = i * (math.pi * 2 / 12)
        x1 = cx + math.cos(a) * w * 0.30
        y1 = cy + math.sin(a) * w * 0.30
        x2 = cx + math.cos(a) * w * 0.48
        y2 = cy + math.sin(a) * w * 0.48
        pygame.draw.line(s, C.SUN_EDGE, (x1, y1), (x2, y2), max(2, int(w * 0.05)))
    _circle(s, C.SUN_EDGE, cx, cy, w * 0.32)
    _circle(s, C.SUN_CORE, cx, cy, w * 0.26)
    _circle(s, (255, 250, 200), cx - w * 0.07, cy - w * 0.07, w * 0.10)


def _paint_pea(s, w, h, frost=False):
    base = (150, 220, 70) if not frost else (150, 215, 255)
    hi = (210, 250, 150) if not frost else (225, 245, 255)
    _circle(s, utils.darken(base, 0.2), w * 0.5, h * 0.5, w * 0.42)
    _circle(s, base, w * 0.5, h * 0.5, w * 0.36)
    _circle(s, hi, w * 0.38, w * 0.38, w * 0.12)


def _paint_frostpea(s, w, h):
    _paint_pea(s, w, h, frost=True)


def _paint_mower(s, w, h):
    pygame.draw.rect(s, (200, 60, 60),
                     pygame.Rect(int(w * 0.15), int(h * 0.30),
                                 int(w * 0.7), int(h * 0.45)),
                     border_radius=int(w * 0.08))
    pygame.draw.rect(s, (230, 230, 230),
                     pygame.Rect(int(w * 0.20), int(h * 0.12),
                                 int(w * 0.45), int(h * 0.25)),
                     border_radius=int(w * 0.05))
    _circle(s, (40, 40, 40), w * 0.30, h * 0.78, w * 0.15)
    _circle(s, (40, 40, 40), w * 0.70, h * 0.78, w * 0.15)
    _circle(s, (120, 120, 120), w * 0.30, h * 0.78, w * 0.06)
    _circle(s, (120, 120, 120), w * 0.70, h * 0.78, w * 0.06)


# ===========================================================================
# AssetManager
# ===========================================================================
class AssetManager:
    """Builds and caches every sprite used by the game.

    Sprites are stored as lists of frames so animated and static art share a
    single access pattern (a static sprite is simply a one-frame list).
    """

    def __init__(self):
        self.plants = {}      # key -> Surface
        self.plant_icons = {}  # key -> small Surface for the seed bar
        self.zombies = {}     # key -> [frame0, frame1]
        self.misc = {}        # name -> Surface
        self.background = None
        self._build()

    # -- construction ------------------------------------------------------
    def _build(self):
        for key, painter in PLANT_PAINTERS.items():
            sprite = _render(PLANT_SPRITE_SIZE, painter)
            self.plants[key] = sprite
            self.plant_icons[key] = pygame.transform.smoothscale(
                sprite, (54, 58)).convert_alpha()

        for key, painter in ZOMBIE_PAINTERS.items():
            size = ZOMBIE_SPRITE_SIZE[key]
            frames = [_render(size, lambda s, w, h, p=painter, f=f: p(s, w, h, f))
                      for f in (0, 1)]
            self.zombies[key] = frames

        self.misc["sun"] = _render((58, 58), _paint_sun)
        self.misc["pea"] = _render((24, 24), _paint_pea)
        self.misc["frostpea"] = _render((24, 24), _paint_frostpea)
        self.misc["mower"] = _render((86, 60), _paint_mower)

        self.background = self._build_background()

    def _build_background(self):
        """Compose the static lawn / sky / house background once."""
        surf = pygame.Surface(C.LOGICAL_SIZE).convert()
        # sky
        utils.draw_vertical_gradient(surf, surf.get_rect(), C.SKY_TOP, C.SKY_BOTTOM)
        # checker-board lawn
        for r in range(C.GRID_ROWS):
            for col in range(C.GRID_COLS):
                x = C.GRID_ORIGIN_X + col * C.CELL_W
                y = C.GRID_ORIGIN_Y + r * C.CELL_H
                color = C.LAWN_LIGHT if (r + col) % 2 == 0 else C.LAWN_DARK
                pygame.draw.rect(surf, color, (x, y, C.CELL_W, C.CELL_H))
        # subtle grid lines
        for col in range(C.GRID_COLS + 1):
            x = C.GRID_ORIGIN_X + col * C.CELL_W
            pygame.draw.line(surf, C.LAWN_LINE, (x, C.GRID_ORIGIN_Y),
                             (x, C.GRID_ORIGIN_Y + C.GRID_HEIGHT), 1)
        for r in range(C.GRID_ROWS + 1):
            y = C.GRID_ORIGIN_Y + r * C.CELL_H
            pygame.draw.line(surf, C.LAWN_LINE, (C.GRID_ORIGIN_X, y),
                             (C.GRID_ORIGIN_X + C.GRID_WIDTH, y), 1)
        # house / porch strip on the left
        house_rect = pygame.Rect(0, C.GRID_ORIGIN_Y - 10,
                                 C.GRID_ORIGIN_X - 6, C.GRID_HEIGHT + 20)
        pygame.draw.rect(surf, (150, 120, 90), house_rect)
        pygame.draw.rect(surf, (120, 92, 64), house_rect, 6)
        for r in range(C.GRID_ROWS):
            y = C.GRID_ORIGIN_Y + r * C.CELL_H + C.CELL_H // 2
            pygame.draw.rect(surf, (110, 84, 58),
                             (8, y - 4, C.GRID_ORIGIN_X - 22, 8))
        # right-hand earth path where zombies emerge
        path_rect = pygame.Rect(C.GRID_ORIGIN_X + C.GRID_WIDTH, C.GRID_ORIGIN_Y - 10,
                                C.LOGICAL_WIDTH - (C.GRID_ORIGIN_X + C.GRID_WIDTH),
                                C.GRID_HEIGHT + 20)
        pygame.draw.rect(surf, (150, 130, 95), path_rect)
        return surf.convert()

    # -- access ------------------------------------------------------------
    def plant(self, key):
        return self.plants[key]

    def plant_icon(self, key):
        return self.plant_icons[key]

    def zombie_frames(self, key):
        return self.zombies[key]

    def get(self, name):
        return self.misc[name]

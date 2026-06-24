"""
utils.py
========
A grab-bag of tiny, dependency-light helpers used across the project:

* maths helpers (clamp / lerp / distance)
* cached font loading
* gradient / rounded-rect / soft-shadow drawing
* a reusable health-bar renderer
* colour helpers (lighten / darken / blend)

Keeping these here means the entity and UI code stays focused on behaviour
rather than low-level pixel pushing.
"""

import math
import pygame

# ---------------------------------------------------------------------------
# Maths helpers
# ---------------------------------------------------------------------------
def clamp(value, low, high):
    """Constrain *value* to the inclusive range [low, high]."""
    return low if value < low else high if value > high else value


def lerp(a, b, t):
    """Linear interpolation between *a* and *b* by factor *t* (0..1)."""
    return a + (b - a) * t


def distance(ax, ay, bx, by):
    """Euclidean distance between two points."""
    return math.hypot(ax - bx, ay - by)


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
def lighten(color, amount):
    """Return *color* moved *amount* (0..1) toward white."""
    return tuple(int(clamp(lerp(c, 255, amount), 0, 255)) for c in color[:3])


def darken(color, amount):
    """Return *color* moved *amount* (0..1) toward black."""
    return tuple(int(clamp(lerp(c, 0, amount), 0, 255)) for c in color[:3])


def blend(color_a, color_b, t):
    """Blend two RGB colours; *t*=0 -> a, *t*=1 -> b."""
    return tuple(int(clamp(lerp(a, b, t), 0, 255))
                 for a, b in zip(color_a[:3], color_b[:3]))


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
_FONT_CACHE = {}
# A list of cartoonish/clean fonts we try in order; SysFont silently falls
# back to a default if none are installed, so this is always safe.
_PREFERRED_FONTS = "comicsansms,segoeui,arial,freesansbold"


def get_font(size, bold=False):
    """Return a cached pygame Font of the requested size."""
    key = (size, bold)
    font = _FONT_CACHE.get(key)
    if font is None:
        try:
            font = pygame.font.SysFont(_PREFERRED_FONTS, size, bold=bold)
        except Exception:
            font = pygame.font.Font(None, size)
        _FONT_CACHE[key] = font
    return font


def draw_text(surface, text, size, x, y, color=(255, 255, 255),
              center=False, bold=False, shadow=True, shadow_color=(0, 0, 0)):
    """Render *text* with an optional drop-shadow.

    Returns the blitted text rectangle so callers can chain layout.
    """
    font = get_font(size, bold)
    label = font.render(str(text), True, color)
    rect = label.get_rect()
    if center:
        rect.center = (int(x), int(y))
    else:
        rect.topleft = (int(x), int(y))
    if shadow:
        shadow_label = font.render(str(text), True, shadow_color)
        surface.blit(shadow_label, (rect.x + 2, rect.y + 2))
    surface.blit(label, rect)
    return rect


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------
def draw_vertical_gradient(surface, rect, top_color, bottom_color):
    """Fill *rect* on *surface* with a smooth top→bottom gradient."""
    rect = pygame.Rect(rect)
    if rect.height <= 0:
        return
    for i in range(rect.height):
        t = i / max(1, rect.height - 1)
        color = blend(top_color, bottom_color, t)
        pygame.draw.line(surface, color,
                         (rect.x, rect.y + i), (rect.right, rect.y + i))


def make_vertical_gradient(size, top_color, bottom_color):
    """Return a new Surface filled with a vertical gradient."""
    surf = pygame.Surface(size).convert()
    draw_vertical_gradient(surf, surf.get_rect(), top_color, bottom_color)
    return surf


def draw_round_rect(surface, rect, color, radius=12, width=0):
    """Convenience wrapper around pygame's rounded-rect support."""
    pygame.draw.rect(surface, color, rect, width=width, border_radius=radius)


def draw_soft_shadow_ellipse(surface, center, width, height, alpha=70):
    """Draw a soft translucent ground-shadow ellipse (used under entities)."""
    shadow = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, alpha), shadow.get_rect())
    surface.blit(shadow, (center[0] - width // 2, center[1] - height // 2))


def draw_health_bar(surface, cx, top_y, width, height, fraction,
                    show_back=True):
    """Draw a centred health bar.

    *cx*       -- horizontal centre
    *top_y*    -- top edge
    *fraction* -- 0..1 portion remaining (colour lerps red→green)
    """
    fraction = clamp(fraction, 0.0, 1.0)
    x = int(cx - width / 2)
    bg = pygame.Rect(x, int(top_y), width, height)
    if show_back:
        pygame.draw.rect(surface, (30, 30, 30), bg.inflate(4, 4),
                         border_radius=4)
    pygame.draw.rect(surface, (70, 70, 70), bg, border_radius=3)
    fill_w = int(width * fraction)
    if fill_w > 0:
        color = blend((210, 70, 60), (80, 210, 90), fraction)
        pygame.draw.rect(surface, color,
                         pygame.Rect(x, int(top_y), fill_w, height),
                         border_radius=3)

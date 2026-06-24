"""
ui.py
=====
Reusable user-interface widgets:

* :class:`Button`   -- a rounded, hover-aware clickable button.
* :class:`SeedCard` -- one plant card in the selection bar (icon, cost,
  cooldown sweep, affordability dimming, selection glow).
* :class:`SeedBar`  -- the top selection bar plus the shovel tool.
* :class:`HUD`      -- sun counter, score, level name, wave meter, pause button
  and transient toast notifications.

All widgets work in the game's fixed *logical* coordinate space; the game is
responsible for translating real window/mouse coordinates into that space.
"""

import math

import pygame

import config as C
from src import utils


# ---------------------------------------------------------------------------
# Generic button
# ---------------------------------------------------------------------------
class Button:
    """A rounded rectangular button with hover and press feedback."""

    def __init__(self, rect, label, font_size=30, action=None,
                 base_color=C.UI_PANEL, text_color=C.UI_TEXT):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font_size = font_size
        self.action = action
        self.base_color = base_color
        self.text_color = text_color
        self.enabled = True

    def hit(self, pos):
        return self.enabled and self.rect.collidepoint(pos)

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos) and self.enabled
        color = self.base_color
        if not self.enabled:
            color = utils.darken(self.base_color, 0.35)
        elif hovered:
            color = utils.lighten(self.base_color, 0.18)
        # drop shadow
        shadow = self.rect.move(0, 4)
        pygame.draw.rect(surface, utils.darken(self.base_color, 0.45),
                         shadow, border_radius=14)
        pygame.draw.rect(surface, color, self.rect, border_radius=14)
        pygame.draw.rect(surface, utils.darken(color, 0.3), self.rect,
                         width=3, border_radius=14)
        utils.draw_text(surface, self.label, self.font_size,
                        self.rect.centerx, self.rect.centery,
                        color=self.text_color, center=True, bold=True,
                        shadow=False)


# ---------------------------------------------------------------------------
# Seed selection bar
# ---------------------------------------------------------------------------
CARD_W, CARD_H = 80, 94
CARD_GAP = 6


class SeedCard:
    """A single selectable plant card."""

    def __init__(self, key, rect):
        self.key = key
        self.rect = pygame.Rect(rect)
        self.data = C.PLANT_DATA[key]

    def draw(self, surface, assets, affordable, cooldown_frac, selected):
        # base card
        pygame.draw.rect(surface, C.UI_PANEL_LIGHT, self.rect, border_radius=8)
        pygame.draw.rect(surface, utils.darken(C.UI_PANEL_DARK, 0.1),
                         self.rect, width=2, border_radius=8)

        # plant icon
        icon = assets.plant_icon(self.key)
        surface.blit(icon, icon.get_rect(center=(self.rect.centerx,
                                                 self.rect.y + 34)))

        # cost label
        cost_color = C.UI_TEXT if affordable else (180, 60, 50)
        utils.draw_text(surface, self.data["cost"], 22, self.rect.centerx,
                        self.rect.bottom - 14, color=cost_color, center=True,
                        bold=True, shadow=False)

        # cooldown sweep (dark overlay receding downward)
        if cooldown_frac > 0:
            ov = pygame.Surface((self.rect.width,
                                 int(self.rect.height * cooldown_frac)),
                                pygame.SRCALPHA)
            ov.fill((20, 20, 30, 150))
            surface.blit(ov, self.rect.topleft)

        # unaffordable dimming
        if not affordable and cooldown_frac <= 0:
            ov = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            ov.fill((20, 20, 30, 110))
            surface.blit(ov, self.rect.topleft)

        # selection glow
        if selected:
            pygame.draw.rect(surface, C.UI_ACCENT, self.rect, width=4,
                             border_radius=8)


class SeedBar:
    """The horizontal plant-selection bar plus the shovel tool."""

    def __init__(self):
        self.cards = []
        x = 150
        y = 14
        for key in C.PLANT_ORDER:
            self.cards.append(SeedCard(key, (x, y, CARD_W, CARD_H)))
            x += CARD_W + CARD_GAP
        # shovel sits just after the last card
        self.shovel_rect = pygame.Rect(x + 6, y + 8, 64, CARD_H - 16)

    def card_at(self, pos):
        for card in self.cards:
            if card.rect.collidepoint(pos):
                return card.key
        return None

    def shovel_at(self, pos):
        return self.shovel_rect.collidepoint(pos)

    def draw(self, surface, game):
        for card in self.cards:
            cd = game.plant_cooldowns.get(card.key, 0.0)
            full = C.PLANT_DATA[card.key]["cooldown"]
            cd_frac = cd / full if full else 0.0
            affordable = game.sun >= card.data["cost"] and cd <= 0
            selected = (game.selected_plant == card.key)
            card.draw(surface, game.assets, affordable, cd_frac, selected)

        # shovel button
        sel = game.shovel_selected
        pygame.draw.rect(surface, C.UI_PANEL_LIGHT, self.shovel_rect,
                         border_radius=8)
        pygame.draw.rect(surface, utils.darken(C.UI_PANEL_DARK, 0.1),
                         self.shovel_rect, width=2, border_radius=8)
        cx, cy = self.shovel_rect.center
        # little shovel glyph
        pygame.draw.rect(surface, (130, 90, 60),
                         (cx - 3, cy - 18, 6, 24))
        pygame.draw.polygon(surface, (180, 185, 190),
                            [(cx - 12, cy + 4), (cx + 12, cy + 4),
                             (cx + 8, cy + 20), (cx - 8, cy + 20)])
        if sel:
            pygame.draw.rect(surface, C.UI_ACCENT, self.shovel_rect, width=4,
                             border_radius=8)


# ---------------------------------------------------------------------------
# Heads-up display
# ---------------------------------------------------------------------------
class Toast:
    """A transient notification (e.g. an unlocked achievement)."""

    __slots__ = ("text", "subtext", "life", "max_life")

    def __init__(self, text, subtext="", life=3.0):
        self.text = text
        self.subtext = subtext
        self.life = life
        self.max_life = life


class HUD:
    """Draws all in-play status information and owns toast notifications."""

    def __init__(self):
        self.toasts = []
        self.pause_rect = pygame.Rect(C.LOGICAL_WIDTH - 60, 18, 42, 42)

    def add_toast(self, text, subtext=""):
        self.toasts.append(Toast(text, subtext))

    def update(self, dt):
        for t in self.toasts:
            t.life -= dt
        self.toasts = [t for t in self.toasts if t.life > 0]

    # -- sub-renderers -----------------------------------------------------
    def _draw_sun_counter(self, surface, assets, sun):
        rect = pygame.Rect(14, 14, 128, 94)
        pygame.draw.rect(surface, C.UI_PANEL, rect, border_radius=10)
        pygame.draw.rect(surface, utils.darken(C.UI_PANEL_DARK, 0.1), rect,
                         width=3, border_radius=10)
        icon = pygame.transform.smoothscale(assets.get("sun"), (40, 40))
        surface.blit(icon, (rect.x + 8, rect.y + 26))
        utils.draw_text(surface, "SUN", 18, rect.centerx + 12, rect.y + 16,
                        color=C.UI_TEXT, center=True, shadow=False, bold=True)
        utils.draw_text(surface, int(sun), 30, rect.x + 54, rect.y + 38,
                        color=C.UI_TEXT, shadow=False, bold=True)

    def _draw_wave_meter(self, surface, game):
        wm = game.wave_manager
        if wm is None:
            return
        x, y, w, h = C.LOGICAL_WIDTH - 380, 90, 280, 16
        pygame.draw.rect(surface, (60, 50, 40), (x, y, w, h), border_radius=9)
        frac = wm.progress_fraction()
        if frac > 0:
            pygame.draw.rect(surface, (200, 80, 70),
                             (x, y, int(w * frac), h), border_radius=9)
        # wave tick marks
        for i in range(1, wm.total_waves):
            mx = x + int(w * i / wm.total_waves)
            pygame.draw.line(surface, (40, 30, 20), (mx, y), (mx, y + h), 2)
        # little flag at the end
        pygame.draw.rect(surface, (30, 25, 18), (x + w - 2, y - 8, 4, h + 12))
        pygame.draw.polygon(surface, (210, 60, 60),
                            [(x + w + 2, y - 8), (x + w + 18, y - 4),
                             (x + w + 2, y)])
        utils.draw_text(surface, f"Wave {wm.current_wave}/{wm.total_waves}",
                        18, x, y - 22, color=C.WHITE, bold=True)

    def _draw_toasts(self, surface):
        for i, t in enumerate(self.toasts):
            appear = 1.0 - max(0.0, (t.life - (t.max_life - 0.3)) / 0.3)
            fade = min(1.0, t.life / 0.4)
            alpha = int(255 * min(appear, fade))
            w, h = 360, 64
            y = 130 + i * (h + 10)
            panel = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(panel, (40, 35, 28, min(230, alpha)),
                             panel.get_rect(), border_radius=12)
            pygame.draw.rect(panel, (240, 200, 90, alpha), panel.get_rect(),
                             width=3, border_radius=12)
            surface.blit(panel, (C.LOGICAL_WIDTH // 2 - w // 2, y))
            cx = C.LOGICAL_WIDTH // 2
            utils.draw_text(surface, t.text, 24, cx, y + 20,
                            color=(255, 220, 110), center=True, bold=True)
            if t.subtext:
                utils.draw_text(surface, t.subtext, 18, cx, y + 44,
                                color=C.WHITE, center=True)

    # -- main --------------------------------------------------------------
    def draw(self, surface, game):
        # top bar background panel
        bar = pygame.Surface((C.LOGICAL_WIDTH, C.TOP_BAR_HEIGHT),
                             pygame.SRCALPHA)
        bar.fill((30, 24, 16, 120))
        surface.blit(bar, (0, 0))

        self._draw_sun_counter(surface, game.assets, game.sun)
        game.seed_bar.draw(surface, game)

        # score / level info (right of centre)
        info_x = C.LOGICAL_WIDTH - 380
        utils.draw_text(surface, f"Score {game.score}", 24, info_x, 10,
                        color=C.WHITE, bold=True)
        utils.draw_text(surface, game.wave_manager.level_name
                        if game.wave_manager else "", 20, info_x, 40,
                        color=(255, 235, 180), bold=True)
        self._draw_wave_meter(surface, game)

        # pause button
        pygame.draw.rect(surface, C.UI_PANEL, self.pause_rect,
                         border_radius=8)
        pygame.draw.rect(surface, utils.darken(C.UI_PANEL_DARK, 0.1),
                         self.pause_rect, width=2, border_radius=8)
        px, py = self.pause_rect.center
        pygame.draw.rect(surface, C.UI_TEXT, (px - 8, py - 9, 5, 18))
        pygame.draw.rect(surface, C.UI_TEXT, (px + 3, py - 9, 5, 18))

        self._draw_toasts(surface)

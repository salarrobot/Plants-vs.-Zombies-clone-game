"""
plants.py
=========
Every plant type, built on a common :class:`Plant` base.

Design notes
------------
* Plants are deliberately *thin*: they read the world through the ``game``
  object passed in (zombie list, particle system, sound, upgrades) and act on
  it, rather than owning references to every other entity.
* Animation is procedural -- a small sine-based bob plus per-plant flourishes
  (a firing recoil, a sunflower head sway) -- so no sprite sheets are needed
  while plants still feel alive.
* Upgrade modifiers (extra health / pea damage) are pulled from the game so the
  shop can influence gameplay without the plants hard-coding anything.
"""

import math

import pygame

import config as C
from src import utils
from src.projectiles import Pea


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------
class Plant:
    """Base class for all plants. Subclasses implement :meth:`act`."""

    key = "plant"

    def __init__(self, row, col, game):
        self.row = row
        self.col = col
        self.game = game
        self.data = C.PLANT_DATA[self.key]

        armor = 1.0 + 0.15 * game.get_upgrade_level("plant_armor")
        self.max_health = self.data["health"] * armor
        self.health = self.max_health

        self.x = C.GRID_ORIGIN_X + col * C.CELL_W + C.CELL_W / 2
        self.y = C.GRID_ORIGIN_Y + row * C.CELL_H + C.CELL_H / 2
        self.alive = True

        self.anim_time = 0.0
        self.recoil = 0.0          # brief offset used by shooters
        self.flash = 0.0           # white flash timer when damaged

    # -- combat ------------------------------------------------------------
    def take_damage(self, amount):
        self.health -= amount
        self.flash = 0.12
        if self.health <= 0:
            self.health = 0
            self.alive = False

    @property
    def health_fraction(self):
        return self.health / self.max_health if self.max_health else 0.0

    # -- per-frame ---------------------------------------------------------
    def update(self, dt):
        self.anim_time += dt
        if self.recoil > 0:
            self.recoil = max(0.0, self.recoil - dt * 5)
        if self.flash > 0:
            self.flash = max(0.0, self.flash - dt)
        self.act(dt)

    def act(self, dt):
        """Override in subclasses for active behaviour."""

    # -- rendering ---------------------------------------------------------
    def _sprite_offset(self):
        """Return (dx, dy) for idle bob plus shooter recoil."""
        bob = math.sin(self.anim_time * 3 + self.col) * 2.0
        return (-self.recoil * 8, bob)

    def draw(self, surface, assets):
        sprite = assets.plant(self.key)
        dx, dy = self._sprite_offset()
        # ground shadow
        utils.draw_soft_shadow_ellipse(
            surface, (self.x, self.y + C.CELL_H * 0.34),
            int(C.CELL_W * 0.5), int(C.CELL_H * 0.18), alpha=60)
        rect = sprite.get_rect(midbottom=(int(self.x + dx),
                                          int(self.y + C.CELL_H * 0.36 + dy)))
        surface.blit(sprite, rect)
        if self.flash > 0:
            self._draw_flash(surface, sprite, rect)
        self._draw_extra(surface, rect)
        if self.health_fraction < 0.999:
            utils.draw_health_bar(surface, self.x, rect.top - 10, 56, 7,
                                  self.health_fraction)

    def _draw_flash(self, surface, sprite, rect):
        mask = sprite.copy()
        mask.fill((255, 255, 255, int(160 * (self.flash / 0.12))),
                  special_flags=pygame.BLEND_RGBA_MULT)
        white = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
        white.fill((255, 255, 255, int(150 * (self.flash / 0.12))))
        white.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(white, rect)

    def _draw_extra(self, surface, rect):
        """Hook for per-plant overlays (cracks, fuse glow, ...)."""


# ---------------------------------------------------------------------------
# Sunflower -- generates sun
# ---------------------------------------------------------------------------
class Sunflower(Plant):
    key = "sunflower"

    def __init__(self, row, col, game):
        super().__init__(row, col, game)
        # first sun comes a little sooner so the player isn't starved
        self.timer = self.data["sun_interval"] * 0.45
        self.glow = 0.0

    def act(self, dt):
        self.timer -= dt
        self.glow = max(0.0, self.glow - dt)
        if self.timer <= 0:
            self.timer = self.data["sun_interval"]
            self.glow = 0.5
            self.game.spawn_plant_sun(self.x, self.y - 10,
                                      self.data["sun_value"])

    def _sprite_offset(self):
        # gentle head sway
        sway = math.sin(self.anim_time * 1.6) * 3.0
        bob = math.sin(self.anim_time * 3) * 1.5
        return (sway, bob)

    def _draw_extra(self, surface, rect):
        if self.glow > 0:
            glow = pygame.Surface((90, 90), pygame.SRCALPHA)
            a = int(120 * (self.glow / 0.5))
            pygame.draw.circle(glow, (255, 240, 150, a), (45, 45), 40)
            surface.blit(glow, glow.get_rect(center=rect.center),
                         special_flags=pygame.BLEND_RGBA_ADD)


# ---------------------------------------------------------------------------
# Peashooter -- fires peas at zombies in its row
# ---------------------------------------------------------------------------
class Peashooter(Plant):
    key = "peashooter"
    frost = False
    sound = "shoot"

    def __init__(self, row, col, game):
        super().__init__(row, col, game)
        self.cooldown = 0.0

    def act(self, dt):
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.cooldown <= 0 and self.game.zombie_in_row_ahead(self.row, self.x):
            self._fire()
            self.cooldown = self.data["fire_interval"]

    def _fire(self):
        bonus = 5 * self.game.get_upgrade_level("pea_power")
        damage = self.data["pea_damage"] + bonus
        pea = Pea(self.x + 28, self.y - 6, self.row, damage, frost=self.frost)
        self.game.add_projectile(pea)
        self.recoil = 1.0
        self.game.sound.play(self.sound)


class IcePeashooter(Peashooter):
    key = "icepea"
    frost = True
    sound = "frost"


# ---------------------------------------------------------------------------
# Wall-nut -- pure defensive wall
# ---------------------------------------------------------------------------
class WallNut(Plant):
    key = "wallnut"

    def _draw_extra(self, surface, rect):
        # progressively show cracks as it takes damage
        frac = self.health_fraction
        if frac < 0.66:
            pygame.draw.line(surface, (60, 40, 20),
                             (rect.centerx - 6, rect.centery - 14),
                             (rect.centerx + 4, rect.centery + 6), 2)
        if frac < 0.33:
            pygame.draw.line(surface, (60, 40, 20),
                             (rect.centerx + 10, rect.centery - 10),
                             (rect.centerx + 2, rect.centery + 16), 2)


# ---------------------------------------------------------------------------
# Cherry Bomb -- area-of-effect single use explosive
# ---------------------------------------------------------------------------
class CherryBomb(Plant):
    key = "cherrybomb"

    def __init__(self, row, col, game):
        super().__init__(row, col, game)
        self.fuse = self.data["fuse"]
        self.exploded = False

    def take_damage(self, amount):
        # invulnerable until it goes off
        pass

    def act(self, dt):
        self.fuse -= dt
        if self.fuse <= 0 and not self.exploded:
            self._explode()

    def _explode(self):
        self.exploded = True
        self.alive = False
        radius = self.data["blast_radius_cells"] * C.CELL_W
        damage = self.data["blast_damage"]
        killed = 0
        for zombie in list(self.game.zombies):
            if utils.distance(self.x, self.y, zombie.x, zombie.y) <= radius:
                was_alive = zombie.alive
                zombie.take_damage(damage)
                if was_alive and not zombie.alive:
                    killed += 1
        self.game.particles.explosion(self.x, self.y)
        self.game.sound.play("explode")
        self.game.add_shake(14)
        self.game.notify_cherry_kills(killed)

    def _sprite_offset(self):
        # swell as the fuse burns down
        t = 1.0 - max(0.0, self.fuse / self.data["fuse"])
        return (0, -math.sin(t * math.pi) * 4)

    def _draw_extra(self, surface, rect):
        # red warning glow that intensifies as it is about to blow
        t = 1.0 - max(0.0, self.fuse / self.data["fuse"])
        glow = pygame.Surface((120, 120), pygame.SRCALPHA)
        a = int(120 * t)
        pygame.draw.circle(glow, (255, 80, 40, a), (60, 60), int(30 + 20 * t))
        surface.blit(glow, glow.get_rect(center=rect.center),
                     special_flags=pygame.BLEND_RGBA_ADD)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
PLANT_CLASSES = {
    "sunflower": Sunflower,
    "peashooter": Peashooter,
    "wallnut": WallNut,
    "icepea": IcePeashooter,
    "cherrybomb": CherryBomb,
}


def create_plant(key, row, col, game):
    """Instantiate the plant registered under *key*."""
    return PLANT_CLASSES[key](row, col, game)

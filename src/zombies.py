"""
zombies.py
==========
Every zombie type, built on a shared :class:`Zombie` base.

Behaviour summary
-----------------
* A zombie walks left along its row at ``speed`` px/s.
* When it reaches a plant it stops and *eats*, dealing ``damage`` every
  :data:`config.ZOMBIE_EAT_INTERVAL` seconds until the plant dies.
* Snow-pea hits apply a temporary *slow* (``slow_timer``) that halves speed and
  tints the zombie blue.
* On death the zombie plays a short topple/fade animation before being removed.

The game loop owns collision and scoring; the zombie only reports its state.
"""

import math

import pygame

import config as C
from src import utils


class Zombie:
    """Base walking enemy."""

    key = "normal"

    def __init__(self, row, game, health_mult=1.0, speed_mult=1.0):
        self.row = row
        self.game = game
        self.data = C.ZOMBIE_DATA[self.key]

        self.max_health = self.data["health"] * health_mult
        self.health = self.max_health
        self.base_speed = self.data["speed"] * speed_mult
        self.damage = self.data["damage"]
        self.reward = self.data["reward"]

        self.x = float(C.ZOMBIE_SPAWN_X)
        self.y = C.GRID_ORIGIN_Y + row * C.CELL_H + C.CELL_H * 0.5

        self.alive = True          # active threat
        self.dying = False         # playing death animation
        self.dead = False          # ready to be removed
        self.death_processed = False
        self.death_timer = 0.0

        self.slow_timer = 0.0
        self.eat_timer = 0.0
        self.frame = 0
        self.frame_timer = 0.0
        self.bob = 0.0

    # -- combat ------------------------------------------------------------
    def take_damage(self, amount):
        if not self.alive:
            return
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            self.dying = True
            self.death_timer = 0.55

    def apply_slow(self, duration):
        self.slow_timer = max(self.slow_timer, duration)

    @property
    def speed(self):
        return self.base_speed * (C.SLOW_FACTOR if self.slow_timer > 0 else 1.0)

    @property
    def health_fraction(self):
        return self.health / self.max_health if self.max_health else 0.0

    @property
    def width(self):
        return self.game.assets.zombie_frames(self.key)[0].get_width()

    # -- per-frame ---------------------------------------------------------
    def update(self, dt):
        if self.slow_timer > 0:
            self.slow_timer = max(0.0, self.slow_timer - dt)

        if self.dying:
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.dead = True
            return

        # walk-cycle animation
        self.frame_timer += dt
        anim_speed = 0.18 if self.speed > 0 else 0.3
        if self.frame_timer >= anim_speed:
            self.frame_timer = 0.0
            self.frame ^= 1
        self.bob = math.sin(self.frame_timer * 20) * 1.0

        target = self.game.plant_blocking(self.row, self.x)
        if target is not None:
            self._eat(dt, target)
        else:
            self.x -= self.speed * dt

    def _eat(self, dt, plant):
        self.eat_timer += dt
        if self.eat_timer >= C.ZOMBIE_EAT_INTERVAL:
            self.eat_timer = 0.0
            plant.take_damage(self.damage)
            self.game.particles.dust(plant.x, plant.y)

    # -- rendering ---------------------------------------------------------
    def _current_sprite(self):
        frames = self.game.assets.zombie_frames(self.key)
        sprite = frames[self.frame]
        if self.slow_timer > 0:
            sprite = sprite.copy()
            sprite.fill((150, 200, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        return sprite

    def draw(self, surface, assets):
        sprite = self._current_sprite()
        foot_y = self.y + C.CELL_H * 0.42

        if self.dying:
            # topple over and fade out
            frac = max(0.0, self.death_timer / 0.55)
            angle = (1.0 - frac) * 80
            sprite = pygame.transform.rotate(sprite, angle)
            sprite = sprite.copy()
            sprite.set_alpha(int(255 * frac))
            rect = sprite.get_rect(center=(int(self.x), int(foot_y - 20)))
            surface.blit(sprite, rect)
            return

        utils.draw_soft_shadow_ellipse(
            surface, (self.x, foot_y), int(self.width * 0.6), 18, alpha=55)
        rect = sprite.get_rect(midbottom=(int(self.x), int(foot_y + self.bob)))
        surface.blit(sprite, rect)

        # health bar
        utils.draw_health_bar(surface, self.x, rect.top - 8,
                              int(self.width * 0.7), 7, self.health_fraction)


# ---------------------------------------------------------------------------
# Concrete zombie types
# ---------------------------------------------------------------------------
class NormalZombie(Zombie):
    key = "normal"


class FastZombie(Zombie):
    key = "fast"


class TankZombie(Zombie):
    key = "tank"


class BossZombie(Zombie):
    key = "boss"

    def __init__(self, row, game, health_mult=1.0, speed_mult=1.0):
        super().__init__(row, game, health_mult, speed_mult)
        # the boss straddles the row a little higher so its bulk reads well
        self.y -= 10


ZOMBIE_CLASSES = {
    "normal": NormalZombie,
    "fast": FastZombie,
    "tank": TankZombie,
    "boss": BossZombie,
}


def create_zombie(key, row, game, health_mult=1.0, speed_mult=1.0):
    """Instantiate the zombie registered under *key*."""
    return ZOMBIE_CLASSES[key](row, game, health_mult, speed_mult)

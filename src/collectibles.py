"""
collectibles.py
===============
The collectable *Sun* token -- the game's core resource.

Sun is produced two ways:
* it falls from the sky at random intervals, and
* Sunflowers periodically pop one out next to themselves.

A token gently falls to a target Y, hovers, pulses, and then fades after a
timeout.  Clicking it (handled by the game loop) adds its value to the
player's sun pool.
"""

import math

import pygame

import config as C
from src import utils


class Sun:
    """A clickable sun token worth :pyattr:`value` sun points."""

    def __init__(self, x, y, value=C.SKY_SUN_VALUE, target_y=None,
                 from_plant=False):
        self.x = float(x)
        self.y = float(y)
        # Sky suns drift to a random resting height; plant suns settle nearby.
        self.target_y = target_y if target_y is not None else y
        self.value = value
        self.from_plant = from_plant
        self.collected = False
        self.alive = True
        self.life = C.SUN_LIFETIME
        self.pulse = 0.0
        self.base_radius = 26
        self.collect_anim = 0.0   # >0 while flying to the sun counter

    @property
    def radius(self):
        return self.base_radius * (1.0 + 0.06 * math.sin(self.pulse * 4))

    def rect(self):
        r = self.base_radius
        return pygame.Rect(int(self.x - r), int(self.y - r), r * 2, r * 2)

    def contains(self, px, py):
        return utils.distance(px, py, self.x, self.y) <= self.base_radius + 6

    def collect(self):
        """Flag the sun as collected; it then animates toward the HUD."""
        if not self.collected:
            self.collected = True
            self.collect_anim = 0.0

    def update(self, dt, hud_target=(70, 30)):
        self.pulse += dt
        if self.collected:
            # fly toward the sun counter then disappear
            self.collect_anim += dt
            tx, ty = hud_target
            self.x += (tx - self.x) * min(1.0, dt * 9)
            self.y += (ty - self.y) * min(1.0, dt * 9)
            if self.collect_anim > 0.45 or utils.distance(
                    self.x, self.y, tx, ty) < 12:
                self.alive = False
            return
        # fall toward resting height
        if self.y < self.target_y:
            self.y = min(self.target_y, self.y + C.SUN_FALL_SPEED * dt)
        # countdown to fade-out
        self.life -= dt
        if self.life <= 0:
            self.alive = False

    def draw(self, surface, assets):
        sprite = assets.get("sun")
        scale = self.radius / (sprite.get_width() / 2)
        if self.collected:
            scale *= max(0.2, 1.0 - self.collect_anim)
        size = max(8, int(sprite.get_width() * scale))
        img = pygame.transform.smoothscale(sprite, (size, size))
        # blink when about to expire
        if not self.collected and self.life < 2.0 and int(self.life * 6) % 2:
            img.set_alpha(120)
        rect = img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(img, rect)

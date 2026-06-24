"""
projectiles.py
==============
Peas fired by the Peashooter and Snow Pea.  A projectile travels rightward
along a single lawn row and is resolved against zombies by the game loop.

Keeping the projectile dumb (it only knows how to move and draw) and letting
the game perform collision keeps responsibilities clean and avoids every pea
needing a reference to the full zombie list.
"""

import math

import pygame

import config as C
from src import utils


class Pea:
    """A single travelling projectile.

    Parameters
    ----------
    x, y   : spawn position (pixels)
    row    : lawn row index used for collision filtering
    damage : hit-points removed from a zombie on impact
    frost  : if True, applies a slow effect and uses the frosty sprite
    """

    def __init__(self, x, y, row, damage, frost=False):
        self.x = float(x)
        self.y = float(y)
        self.row = row
        self.damage = damage
        self.frost = frost
        self.speed = C.PEA_SPEED
        self.radius = C.PEA_RADIUS
        self.alive = True
        self.spin = 0.0

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.radius), int(self.y - self.radius),
                           self.radius * 2, self.radius * 2)

    def update(self, dt):
        self.x += self.speed * dt
        self.spin += dt * 12
        # Despawn once it leaves the right edge of the screen.
        if self.x - self.radius > C.LOGICAL_WIDTH:
            self.alive = False

    def draw(self, surface, assets):
        sprite = assets.get("frostpea" if self.frost else "pea")
        # tiny vertical bob so the pea reads as "alive"
        bob = math.sin(self.spin) * 1.5
        rect = sprite.get_rect(center=(int(self.x), int(self.y + bob)))
        surface.blit(sprite, rect)

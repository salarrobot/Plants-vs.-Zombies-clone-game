"""
effects.py
==========
Lightweight particle systems used for explosions, hit sparks, sun pickups and
floating score/sun text.  A single :class:`ParticleSystem` owns every live
particle so the game loop only needs one update/draw call.

Particles are deliberately simple (gravity + fade) -- they cost almost nothing
and keep the game comfortably above 60 FPS even with hundreds on screen.
"""

import math
import random

import pygame

from src import utils


class Particle:
    """A single physics-driven coloured dot (or small square)."""

    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color",
                 "radius", "gravity", "shrink")

    def __init__(self, x, y, vx, vy, life, color, radius,
                 gravity=400.0, shrink=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.radius = radius
        self.gravity = gravity
        self.shrink = shrink

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        frac = max(0.0, self.life / self.max_life)
        r = self.radius * (frac if self.shrink else 1.0)
        if r < 0.5:
            return
        alpha = int(255 * frac)
        size = int(r * 2) + 2
        dot = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(dot, (*self.color, alpha),
                           (size // 2, size // 2), int(r))
        surface.blit(dot, (self.x - size // 2, self.y - size // 2))


class FloatingText:
    """A short-lived label that drifts upward and fades (e.g. '+25')."""

    __slots__ = ("x", "y", "text", "color", "life", "max_life", "size")

    def __init__(self, x, y, text, color=(255, 255, 255), life=1.0, size=26):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size

    def update(self, dt):
        self.y -= 38 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        frac = max(0.0, self.life / self.max_life)
        font = utils.get_font(self.size, bold=True)
        label = font.render(self.text, True, self.color)
        label.set_alpha(int(255 * frac))
        rect = label.get_rect(center=(int(self.x), int(self.y)))
        shadow = font.render(self.text, True, (0, 0, 0))
        shadow.set_alpha(int(180 * frac))
        surface.blit(shadow, (rect.x + 2, rect.y + 2))
        surface.blit(label, rect)


class ParticleSystem:
    """Container that updates and draws every active particle / floater."""

    def __init__(self):
        self.particles = []
        self.texts = []

    def clear(self):
        self.particles.clear()
        self.texts.clear()

    # -- spawners ----------------------------------------------------------
    def burst(self, x, y, color, count=14, speed=180, radius=4,
              gravity=400, life=0.6):
        """Generic radial burst of particles."""
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(speed * 0.3, speed)
            self.particles.append(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(life * 0.6, life),
                color, random.uniform(radius * 0.6, radius), gravity))

    def explosion(self, x, y):
        """Large fiery explosion for the Cherry Bomb."""
        for _ in range(46):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(80, 360)
            color = random.choice([(255, 200, 60), (255, 120, 40),
                                   (220, 60, 40), (90, 90, 90)])
            self.particles.append(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd,
                random.uniform(0.4, 0.9), color,
                random.uniform(4, 11), gravity=120))

    def hit_spark(self, x, y, color=(220, 240, 120)):
        self.burst(x, y, color, count=8, speed=140, radius=3,
                   gravity=300, life=0.4)

    def sun_sparkle(self, x, y):
        self.burst(x, y, (255, 240, 150), count=12, speed=120, radius=4,
                   gravity=-40, life=0.7)

    def dust(self, x, y):
        self.burst(x, y, (170, 150, 120), count=6, speed=70, radius=3,
                   gravity=200, life=0.5)

    def floating_text(self, x, y, text, color=(255, 255, 255), size=26):
        self.texts.append(FloatingText(x, y, text, color, size=size))

    # -- lifecycle ---------------------------------------------------------
    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]
        self.texts = [t for t in self.texts if t.update(dt)]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)
        for t in self.texts:
            t.draw(surface)

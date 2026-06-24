"""
grid.py
=======
The lawn grid model and the row lawn-mowers.

:class:`Grid` is a thin spatial helper: it converts between pixel coordinates
and (row, col) cells, tracks which cells are occupied, and exposes cell
geometry for highlighting.  It holds references to plants but the game owns the
authoritative plant list -- the grid is purely about *placement*.

:class:`Mower` is the classic last-line-of-defence: one sits at the left of
each row and, when a zombie breaches the house, charges right and clears the
entire row once.
"""

import pygame

import config as C
from src import utils


class Grid:
    """Maps the lawn into a GRID_ROWS x GRID_COLS array of plant slots."""

    def __init__(self):
        # cells[row][col] -> Plant instance or None
        self.cells = [[None for _ in range(C.GRID_COLS)]
                      for _ in range(C.GRID_ROWS)]

    def clear(self):
        for row in self.cells:
            for i in range(len(row)):
                row[i] = None

    # -- coordinate conversion --------------------------------------------
    def cell_at_pixel(self, px, py):
        """Return (row, col) for a pixel, or None if outside the lawn."""
        if not (C.GRID_ORIGIN_X <= px < C.GRID_ORIGIN_X + C.GRID_WIDTH and
                C.GRID_ORIGIN_Y <= py < C.GRID_ORIGIN_Y + C.GRID_HEIGHT):
            return None
        col = int((px - C.GRID_ORIGIN_X) // C.CELL_W)
        row = int((py - C.GRID_ORIGIN_Y) // C.CELL_H)
        return (row, col)

    def cell_rect(self, row, col):
        return pygame.Rect(C.GRID_ORIGIN_X + col * C.CELL_W,
                           C.GRID_ORIGIN_Y + row * C.CELL_H,
                           C.CELL_W, C.CELL_H)

    # -- occupancy ---------------------------------------------------------
    def is_empty(self, row, col):
        return self.cells[row][col] is None

    def place(self, plant):
        self.cells[plant.row][plant.col] = plant

    def remove(self, row, col):
        plant = self.cells[row][col]
        self.cells[row][col] = None
        return plant

    def sync_dead(self):
        """Drop references to plants that have died (eaten / exploded)."""
        for r in range(C.GRID_ROWS):
            for c in range(C.GRID_COLS):
                plant = self.cells[r][c]
                if plant is not None and not plant.alive:
                    self.cells[r][c] = None

    # -- rendering helper --------------------------------------------------
    def draw_cell_highlight(self, surface, row, col, valid=True):
        rect = self.cell_rect(row, col)
        color = (255, 255, 255, 70) if valid else (220, 60, 60, 90)
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay.fill(color)
        surface.blit(overlay, rect.topleft)
        pygame.draw.rect(surface, (255, 255, 255), rect, 2, border_radius=4)


class Mower:
    """A lawn-mower parked at the start of a row.

    States:
        idle      -- waiting at the left edge
        triggered -- charging right, shredding zombies it touches
        spent     -- has crossed the lawn and is gone
    """

    def __init__(self, row):
        self.row = row
        self.x = C.GRID_ORIGIN_X - 52
        self.y = C.GRID_ORIGIN_Y + row * C.CELL_H + C.CELL_H * 0.5
        self.state = "idle"
        self.recharge_timer = 0.0      # used by the Turbo Mowers upgrade

    @property
    def active(self):
        return self.state == "idle"

    def trigger(self):
        if self.state == "idle":
            self.state = "triggered"
            return True
        return False

    def recharge(self):
        if self.state == "spent":
            self.state = "idle"
            self.x = C.GRID_ORIGIN_X - 52
            self.recharge_timer = 0.0

    def update(self, dt, zombies, particles, sound):
        if self.state != "triggered":
            return
        self.x += C.MOWER_SPEED * dt
        for z in zombies:
            if z.row == self.row and z.alive and abs(z.x - self.x) < 50:
                z.take_damage(C.MOWER_DAMAGE)
                particles.burst(z.x, z.y, (200, 200, 200), count=10)
        if self.x > C.LOGICAL_WIDTH + 40:
            self.state = "spent"

    def draw(self, surface, assets):
        if self.state == "spent":
            return
        sprite = assets.get("mower")
        rect = sprite.get_rect(center=(int(self.x), int(self.y + 14)))
        surface.blit(sprite, rect)

"""Rough performance probe: time update+draw+present for a busy scene."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import time
import random
random.seed(3)
import pygame
import config as C
from src.game import Game, PLAYING

DT = 1.0 / 60.0
g = Game()
g.start_run(3)            # a harder level (more zombie variety)
g.sun = 100000
for r in range(C.GRID_ROWS):
    for col, key in ((0, "sunflower"), (1, "peashooter"), (2, "icepea"),
                     (3, "peashooter"), (7, "wallnut")):
        g.selected_plant = key
        g._place_plant(r, col)

# warm up so zombies, peas and particles populate the scene
for _ in range(60 * 18):
    g.sun = 100000
    g._update(DT)

n = 600
t0 = time.perf_counter()
for _ in range(n):
    g.sun = 100000
    g._update(DT)
    g._draw()
    g._present()
elapsed = time.perf_counter() - t0
ms = elapsed / n * 1000
print(f"scene: zombies={len(g.zombies)} plants={len(g.plants)} "
      f"peas={len(g.projectiles)} particles={len(g.particles.particles)}")
print(f"avg frame: {ms:.2f} ms  ->  ~{1000/ms:.0f} FPS headroom")
pygame.quit()
print("PERF TEST DONE")

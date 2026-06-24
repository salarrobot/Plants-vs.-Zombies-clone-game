"""Verify a level is actually winnable: build a defence, fast-forward, expect SHOP."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import random
random.seed(7)
import pygame
import config as C
from src.game import Game, PLAYING, SHOP, GAME_OVER

DT = 1.0 / 60.0
g = Game()
g.start_run(1)
g.sun = 100000

# Plant a solid grid: sunflowers col 0-1, peashooters col 2-3, wall-nuts col 7.
for r in range(C.GRID_ROWS):
    for col, key in ((0, "sunflower"), (1, "peashooter"),
                     (2, "peashooter"), (3, "peashooter"), (7, "wallnut")):
        g.selected_plant = key
        g._place_plant(r, col)
g.sun = 100000

frames = 0
while g.state == PLAYING and frames < 60 * 300:   # up to 5 game-minutes
    # keep sun topped up and re-plant anything eaten in the back rows
    g.sun = 100000
    g._update(DT)
    frames += 1

print(f"finished after {frames/60:.1f}s  state={g.state} "
      f"(SHOP={SHOP}, GAME_OVER={GAME_OVER})  score={g.score} "
      f"kills={g.save.stat('zombies_killed')}")
assert g.state == SHOP, "level 1 should be winnable with a full defence"
pygame.quit()
print("CLEAR TEST PASSED")

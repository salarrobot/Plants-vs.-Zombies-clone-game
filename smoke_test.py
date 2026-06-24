"""Headless smoke test: drive the game through many frames & states.

Runs with dummy SDL drivers so it needs no display or audio device. It does NOT
replace playing the game, but it exercises construction, every menu, a full
play loop with spawning/combat, planting, shop and the win/lose transitions to
catch import errors, typos and crashes.
"""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import random
random.seed(1)

import pygame
import config as C
from src.game import (Game, MENU, LEVEL_SELECT, PLAYING, PAUSED, SHOP,
                      GAME_OVER, VICTORY, HELP)

DT = 1.0 / 60.0


def step(game, frames):
    for _ in range(frames):
        game._update(DT)
        game._draw()
        game._present()


def main():
    g = Game()
    print("constructed OK; sound enabled:", g.sound.enabled)

    # exercise each static screen draw
    for st in (MENU, LEVEL_SELECT, HELP):
        g.state = st
        step(g, 2)
    print("menus draw OK")

    # start a run and play for a while
    g.start_run(1)
    assert g.state == PLAYING
    step(g, 5)

    # plant a sunflower and a peashooter via the public helpers
    g.selected_plant = "sunflower"
    g._place_plant(2, 0)
    g.sun = 9999
    g.selected_plant = "peashooter"
    g._place_plant(2, 1)
    g.selected_plant = "wallnut"
    g._place_plant(2, 3)
    g.selected_plant = "icepea"
    g._place_plant(1, 1)
    print("plants placed:", len(g.plants))

    # run long enough for waves to spawn and combat to happen
    max_seen = 0
    for _ in range(60 * 40):              # ~40 seconds of game time
        g._update(DT)
        max_seen = max(max_seen, len(g.zombies))
        if g.state != PLAYING:
            break
    g._draw(); g._present()
    print("after play loop: state=", g.state, "max zombies seen=", max_seen,
          "score=", g.score, "kills=", g.save.stat("zombies_killed"))

    # force a cherry bomb explosion path
    g.load_level(1)
    g.sun = 9999
    for _ in range(60 * 14):              # let some zombies arrive
        g._update(DT)
        if g.zombies:
            break
    g.selected_plant = "cherrybomb"
    if g.zombies:
        z = g.zombies[0]
        col = max(0, min(C.GRID_COLS - 1,
                         int((z.x - C.GRID_ORIGIN_X) // C.CELL_W)))
        g._place_plant(z.row, col)
    step(g, 90)
    print("cherry bomb path OK; particles:", len(g.particles.particles))

    # shop screen
    g.state = SHOP
    g.save.data["coins"] = 9999
    step(g, 2)
    for key in C.SHOP_ITEMS:
        g._do_action(("buy", key))
    print("shop OK; upgrades:", g.save.data["upgrades"])

    # game over + victory draws
    g.state = GAME_OVER
    step(g, 2)
    g.state = VICTORY
    step(g, 2)
    print("end screens OK")

    # simulate a forced victory to test progression/save
    g.start_run(C.NUM_LEVELS)
    g.complete_level()
    print("final-level complete -> state:", g.state,
          "(expected VICTORY =", VICTORY, ")")

    g.save.save()
    pygame.quit()
    print("\nSMOKE TEST PASSED")


if __name__ == "__main__":
    main()

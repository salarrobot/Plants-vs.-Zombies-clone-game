"""
config.py
=========
Central configuration and constant definitions for the whole game.

Everything that could be considered a "magic number" lives here so that the
rest of the code base contains no hard-coded gameplay values.  Tuning the game
is therefore a matter of editing this single file.

The module is intentionally free of any pygame imports so it can be imported
from anywhere (including unit tests) without a display being initialised.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(ROOT_DIR, "assets")          # optional external art
SAVE_DIR = os.path.join(ROOT_DIR, "saves")             # progress / high scores
SAVE_FILE = os.path.join(SAVE_DIR, "savegame.json")

# ---------------------------------------------------------------------------
# Display / timing
# ---------------------------------------------------------------------------
# All gameplay is drawn onto a fixed "logical" canvas which is then scaled to
# whatever window/full-screen resolution the player chooses.  This gives us
# free, crisp, responsive UI scaling and trivial full-screen support.
LOGICAL_WIDTH = 1280
LOGICAL_HEIGHT = 720
LOGICAL_SIZE = (LOGICAL_WIDTH, LOGICAL_HEIGHT)

DEFAULT_WINDOW_WIDTH = 1280
DEFAULT_WINDOW_HEIGHT = 720

WINDOW_TITLE = "Botanical Brigade  -  a Plants vs Zombies clone"
FPS = 60

# ---------------------------------------------------------------------------
# Lawn grid layout
# ---------------------------------------------------------------------------
GRID_COLS = 9
GRID_ROWS = 5
CELL_W = 110
CELL_H = 100
GRID_ORIGIN_X = 190                      # leaves room on the left for mowers
GRID_ORIGIN_Y = 158
GRID_WIDTH = GRID_COLS * CELL_W
GRID_HEIGHT = GRID_ROWS * CELL_H

TOP_BAR_HEIGHT = 118                      # seed bar / HUD region at the top
LAWN_LEFT_EDGE = GRID_ORIGIN_X           # x past which a zombie means "lose"
ZOMBIE_SPAWN_X = LOGICAL_WIDTH + 60       # zombies appear just off-screen right

# ---------------------------------------------------------------------------
# Colour palette  (cartoon-style, R, G, B)
# ---------------------------------------------------------------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SHADOW = (0, 0, 0, 70)

LAWN_LIGHT = (124, 196, 74)
LAWN_DARK = (104, 176, 58)
LAWN_LINE = (92, 158, 50)

SKY_TOP = (122, 198, 255)
SKY_BOTTOM = (196, 236, 255)

UI_PANEL = (222, 198, 150)
UI_PANEL_DARK = (170, 130, 80)
UI_PANEL_LIGHT = (244, 226, 184)
UI_TEXT = (60, 40, 20)
UI_ACCENT = (240, 180, 60)

SUN_CORE = (255, 236, 120)
SUN_EDGE = (255, 190, 40)

HEALTH_GREEN = (80, 210, 90)
HEALTH_RED = (210, 70, 60)
HEALTH_BACK = (40, 40, 40)

FROST_TINT = (120, 190, 255)

# ---------------------------------------------------------------------------
# Economy
# ---------------------------------------------------------------------------
STARTING_SUN = 75
SKY_SUN_VALUE = 25
SKY_SUN_MIN_INTERVAL = 8.0               # seconds between falling sky-suns
SKY_SUN_MAX_INTERVAL = 13.0
SUN_LIFETIME = 9.0                       # seconds before an uncollected sun fades
SUN_FALL_SPEED = 55                      # px / second

# ---------------------------------------------------------------------------
# Plant definitions
# ---------------------------------------------------------------------------
# Each entry feeds both the gameplay classes and the seed-selection bar.  The
# "key" is the internal identifier used throughout the code base.
PLANT_DATA = {
    "sunflower": {
        "name": "Sunflower",
        "cost": 50,
        "health": 80,
        "cooldown": 7.5,
        "sun_interval": 8.0,
        "sun_value": 25,
    },
    "peashooter": {
        "name": "Peashooter",
        "cost": 100,
        "health": 110,
        "cooldown": 7.5,
        "fire_interval": 1.45,
        "pea_damage": 20,
    },
    "wallnut": {
        "name": "Wall-nut",
        "cost": 50,
        "health": 420,
        "cooldown": 25.0,
    },
    "icepea": {
        "name": "Snow Pea",
        "cost": 175,
        "health": 110,
        "cooldown": 7.5,
        "fire_interval": 1.55,
        "pea_damage": 20,
        "slow_duration": 3.5,
    },
    "cherrybomb": {
        "name": "Cherry Bomb",
        "cost": 150,
        "health": 9999,
        "cooldown": 30.0,
        "fuse": 0.85,
        "blast_damage": 1800,
        "blast_radius_cells": 1.5,
    },
}

# Order the cards appear in the seed bar.
PLANT_ORDER = ["sunflower", "peashooter", "wallnut", "icepea", "cherrybomb"]

# ---------------------------------------------------------------------------
# Projectiles
# ---------------------------------------------------------------------------
PEA_SPEED = 360                          # px / second
PEA_RADIUS = 11

# ---------------------------------------------------------------------------
# Zombie definitions
# ---------------------------------------------------------------------------
ZOMBIE_DATA = {
    "normal": {
        "name": "Browncoat",
        "health": 100,
        "speed": 20,                     # px / second (walking left)
        "damage": 22,                    # damage per second while eating
        "reward": 10,                    # score awarded on death
    },
    "fast": {
        "name": "Track Runner",
        "health": 80,
        "speed": 46,
        "damage": 22,
        "reward": 15,
    },
    "tank": {
        "name": "Buckethead",
        "health": 440,
        "speed": 15,
        "damage": 26,
        "reward": 25,
    },
    "boss": {
        "name": "Gargantuar",
        "health": 2400,
        "speed": 12,
        "damage": 70,
        "reward": 150,
    },
}

ZOMBIE_EAT_INTERVAL = 0.5                 # apply eat-damage twice per second
SLOW_FACTOR = 0.45                        # speed multiplier while frozen

# ---------------------------------------------------------------------------
# Lawn mowers (last-line defence, one per row)
# ---------------------------------------------------------------------------
MOWER_SPEED = 620                         # px / second once triggered
MOWER_DAMAGE = 9999
MOWER_RECHARGE_TIME = 30.0                 # only with the "Turbo Mowers" upgrade

# ---------------------------------------------------------------------------
# Levels & wave generation
# ---------------------------------------------------------------------------
NUM_LEVELS = 5

# Per-level tuning used by the procedural wave generator (see waves.py).
LEVEL_CONFIG = {
    1: {"name": "Front Lawn",     "waves": 3, "types": ["normal"],
        "boss": False, "spawn_scale": 1.00},
    2: {"name": "Backyard",       "waves": 4, "types": ["normal", "fast"],
        "boss": False, "spawn_scale": 1.10},
    3: {"name": "Twilight Pool",  "waves": 4, "types": ["normal", "fast", "tank"],
        "boss": False, "spawn_scale": 1.20},
    4: {"name": "Foggy Roof",     "waves": 5, "types": ["normal", "fast", "tank"],
        "boss": False, "spawn_scale": 1.35},
    5: {"name": "Final Stand",    "waves": 5, "types": ["normal", "fast", "tank"],
        "boss": True,  "spawn_scale": 1.55},
}

# Pacing of the wave system.
FIRST_WAVE_DELAY = 12.0                    # grace period before wave 1
WAVE_INTERVAL = 24.0                       # seconds between scheduled waves
HUGE_WAVE_EVERY = 0                        # (reserved) flag waves; 0 disables

# ---------------------------------------------------------------------------
# Upgrade shop (between levels)
# ---------------------------------------------------------------------------
SHOP_ITEMS = {
    "sun_bonus": {
        "name": "Solar Subsidy",
        "desc": "Start each level with +25 sun.",
        "cost": 150,
        "max_level": 4,
    },
    "pea_power": {
        "name": "Sharpened Peas",
        "desc": "Peashooters deal +5 damage.",
        "cost": 250,
        "max_level": 3,
    },
    "plant_armor": {
        "name": "Reinforced Roots",
        "desc": "All plants gain +15% health.",
        "cost": 250,
        "max_level": 3,
    },
    "fast_mowers": {
        "name": "Turbo Mowers",
        "desc": "Recharge a used lawn-mower each level.",
        "cost": 400,
        "max_level": 1,
    },
}

# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------
ACHIEVEMENTS = {
    "first_blood": {"name": "First Blood", "desc": "Defeat your first zombie."},
    "green_thumb": {"name": "Green Thumb", "desc": "Plant 25 plants."},
    "sun_tycoon":  {"name": "Sun Tycoon", "desc": "Collect 1000 sun in total."},
    "boom":        {"name": "Boom!", "desc": "Vaporise 4+ zombies with one Cherry Bomb."},
    "survivor":    {"name": "Survivor", "desc": "Clear a level without losing a mower."},
    "champion":    {"name": "Champion", "desc": "Beat the final level."},
    "centurion":   {"name": "Centurion", "desc": "Defeat 100 zombies in total."},
}

# ---------------------------------------------------------------------------
# Misc gameplay feel
# ---------------------------------------------------------------------------
SCREEN_SHAKE_DECAY = 7.0                   # how quickly shake settles
PLANT_PLACE_REFUND = 0.0                   # (reserved) refund fraction on dig

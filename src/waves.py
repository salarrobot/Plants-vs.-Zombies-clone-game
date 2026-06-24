"""
waves.py
========
Procedural wave / level generation and scheduling.

The :class:`WaveManager` turns a level's configuration (allowed zombie types,
number of waves, difficulty scale) into a concrete, *randomly generated* set of
waves, then feeds them to the game over time.  Because waves are generated from
a point budget rather than hand-authored lists, every play-through differs and
new levels can be added just by extending :data:`config.LEVEL_CONFIG`.

Pacing rules
------------
* A grace period precedes the first wave.
* Subsequent waves arrive on a timer, but that timer is shortened once the
  lawn is nearly clear so the action never stalls.
* The final wave of every level is a larger "huge wave"; on boss levels it also
  contains the Gargantuar.
"""

import random

import config as C


# Relative "point" cost of each zombie used by the budget-based generator.
ZOMBIE_COST = {"normal": 1.0, "fast": 1.5, "tank": 3.0}
# Spawn weighting -- cheaper zombies appear more often.
ZOMBIE_WEIGHT = {"normal": 1.0, "fast": 0.6, "tank": 0.35}


class WaveManager:
    """Generates and schedules the zombie waves for one level."""

    def __init__(self, game, level):
        self.game = game
        self.level = level
        cfg = C.LEVEL_CONFIG[level]
        self.level_name = cfg["name"]
        self.total_waves = cfg["waves"]
        self.types = cfg["types"]
        self.has_boss = cfg["boss"]
        self.spawn_scale = cfg["spawn_scale"]

        # difficulty scaling applied to every spawned zombie
        self.health_mult = 1.0 + (level - 1) * 0.12
        self.speed_mult = 1.0 + (level - 1) * 0.05

        self.waves = self._generate_waves()

        self.current_wave = 0            # 0 == not started
        self.timer = C.FIRST_WAVE_DELAY  # countdown to next wave
        self.spawn_queue = []            # [[delay, key, row], ...]
        self.banner_timer = 0.0          # HUD "huge wave" flash
        self.is_final_wave = False

    # -- generation --------------------------------------------------------
    def _generate_waves(self):
        """Build a list of waves; each wave is a list of (key, row) spawns."""
        waves = []
        for i in range(self.total_waves):
            is_final = (i == self.total_waves - 1)
            budget = (3 + i * 2 + (self.level - 1) * 1.5) * self.spawn_scale
            if is_final:
                budget *= 1.7                 # the climactic "huge wave"
            spawns = self._spend_budget(budget)
            if is_final and self.has_boss:
                spawns.append(("boss", random.randint(1, C.GRID_ROWS - 2)))
            random.shuffle(spawns)
            waves.append(spawns)
        return waves

    def _spend_budget(self, budget):
        """Pick a random multiset of zombies that costs ~*budget* points."""
        spawns = []
        remaining = budget
        affordable = [t for t in self.types if ZOMBIE_COST.get(t, 99) <= remaining]
        while affordable:
            weights = [ZOMBIE_WEIGHT[t] for t in affordable]
            choice = random.choices(affordable, weights=weights, k=1)[0]
            spawns.append((choice, random.randint(0, C.GRID_ROWS - 1)))
            remaining -= ZOMBIE_COST[choice]
            affordable = [t for t in self.types
                          if ZOMBIE_COST.get(t, 99) <= remaining]
        if not spawns:                       # guarantee at least one zombie
            spawns.append(("normal", random.randint(0, C.GRID_ROWS - 1)))
        return spawns

    # -- scheduling --------------------------------------------------------
    def _start_next_wave(self):
        self.current_wave += 1
        self.is_final_wave = (self.current_wave == self.total_waves)
        wave = self.waves[self.current_wave - 1]
        # stagger the spawns within the wave
        self.spawn_queue = []
        gap = 0.7 if not self.is_final_wave else 0.45
        for j, (key, row) in enumerate(wave):
            self.spawn_queue.append([gap * j + random.uniform(0, 0.4), key, row])
        self.timer = C.WAVE_INTERVAL
        self.banner_timer = 2.5 if self.is_final_wave else 1.2
        self.game.sound.play("wave")
        self.game.on_wave_start(self.current_wave, self.is_final_wave)

    def update(self, dt):
        if self.banner_timer > 0:
            self.banner_timer = max(0.0, self.banner_timer - dt)

        # process active spawn queue
        if self.spawn_queue:
            self.spawn_queue[0][0] -= dt
            while self.spawn_queue and self.spawn_queue[0][0] <= 0:
                _, key, row = self.spawn_queue.pop(0)
                self.game.spawn_zombie(key, row, self.health_mult,
                                       self.speed_mult)

        if self.current_wave >= self.total_waves:
            return  # everything spawned; game checks for clear separately

        # advance the wave timer; hurry it up when the lawn is nearly empty
        self.timer -= dt
        if not self.spawn_queue and self.game.active_zombie_count() <= 1:
            self.timer = min(self.timer, 2.5)
        if self.timer <= 0:
            self._start_next_wave()

    # -- queries -----------------------------------------------------------
    def is_cleared(self):
        """True once every wave has spawned and no zombies remain alive."""
        return (self.current_wave >= self.total_waves and
                not self.spawn_queue and
                self.game.active_zombie_count() == 0)

    def progress_fraction(self):
        """0..1 indicator for the HUD wave meter."""
        if self.total_waves == 0:
            return 1.0
        return min(1.0, self.current_wave / self.total_waves)

    def time_to_next_wave(self):
        if self.current_wave >= self.total_waves:
            return 0.0
        return max(0.0, self.timer)

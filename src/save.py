"""
save.py
=======
Persistent progress: high scores, unlocked levels, shop upgrades, lifetime
stats and achievements -- all stored as a single JSON file under ``saves/``.

:class:`SaveManager` is the single source of truth for anything that should
survive between runs.  Every read goes through helper accessors that fill in
defaults, so a missing or partially-corrupt save never crashes the game.
"""

import json
import os

import config as C


def _default_data():
    """Return a fresh save dict with every expected key populated."""
    return {
        "high_score": 0,
        "highest_level": 1,            # furthest level the player may select
        "coins": 0,                    # currency spent in the upgrade shop
        "upgrades": {k: 0 for k in C.SHOP_ITEMS},
        "achievements": {k: False for k in C.ACHIEVEMENTS},
        "stats": {
            "zombies_killed": 0,
            "plants_placed": 0,
            "sun_collected": 0,
            "levels_cleared": 0,
        },
    }


class SaveManager:
    """Loads, mutates and persists the player's progress."""

    def __init__(self, path=C.SAVE_FILE):
        self.path = path
        self.data = _default_data()
        self.load()

    # -- persistence -------------------------------------------------------
    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as fh:
                    loaded = json.load(fh)
                self._merge(loaded)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[save] could not read save ({exc}); starting fresh.")
            self.data = _default_data()

    def _merge(self, loaded):
        """Deep-merge *loaded* over the defaults so new keys are filled in."""
        base = _default_data()
        for key, default in base.items():
            value = loaded.get(key, default)
            if isinstance(default, dict) and isinstance(value, dict):
                merged = dict(default)
                merged.update(value)
                base[key] = merged
            else:
                base[key] = value
        self.data = base

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, indent=2)
        except OSError as exc:
            print(f"[save] could not write save: {exc}")

    def reset(self):
        self.data = _default_data()
        self.save()

    # -- high score & progress --------------------------------------------
    @property
    def high_score(self):
        return self.data["high_score"]

    def submit_score(self, score):
        """Record *score*; returns True if it is a new high score."""
        if score > self.data["high_score"]:
            self.data["high_score"] = score
            self.save()
            return True
        return False

    @property
    def highest_level(self):
        return self.data["highest_level"]

    def unlock_level(self, level):
        if level > self.data["highest_level"]:
            self.data["highest_level"] = min(level, C.NUM_LEVELS)
            self.save()

    # -- coins / shop ------------------------------------------------------
    @property
    def coins(self):
        return self.data["coins"]

    def add_coins(self, amount):
        self.data["coins"] = max(0, self.data["coins"] + int(amount))

    def upgrade_level(self, key):
        return self.data["upgrades"].get(key, 0)

    def can_buy(self, key):
        item = C.SHOP_ITEMS[key]
        return (self.upgrade_level(key) < item["max_level"] and
                self.coins >= item["cost"])

    def buy_upgrade(self, key):
        """Purchase one level of an upgrade; returns True on success."""
        if not self.can_buy(key):
            return False
        item = C.SHOP_ITEMS[key]
        self.data["coins"] -= item["cost"]
        self.data["upgrades"][key] = self.upgrade_level(key) + 1
        self.save()
        return True

    # -- stats & achievements ---------------------------------------------
    def add_stat(self, name, amount=1):
        self.data["stats"][name] = self.data["stats"].get(name, 0) + amount

    def stat(self, name):
        return self.data["stats"].get(name, 0)

    def is_unlocked(self, key):
        return self.data["achievements"].get(key, False)

    def unlock_achievement(self, key):
        """Unlock an achievement; returns True only the first time."""
        if key in self.data["achievements"] and not self.data["achievements"][key]:
            self.data["achievements"][key] = True
            self.save()
            return True
        return False

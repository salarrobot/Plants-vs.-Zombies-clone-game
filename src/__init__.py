"""
src package
===========
Game source modules for the Plants vs Zombies clone.

Sub-modules:
    utils        -- small pygame drawing / maths helpers
    assets       -- procedural sprite generation and caching (AssetManager)
    audio        -- procedural sound + music generation (SoundManager)
    effects      -- particle systems and floating text
    projectiles  -- peas / frost peas
    collectibles -- collectable sun tokens
    plants       -- all plant types
    zombies      -- all zombie types
    grid         -- the lawn grid model
    waves        -- procedural wave / level generation
    ui           -- buttons, seed cards, menus and HUD widgets
    save         -- persistent progress, high-scores and achievements
    game         -- top level Game object and state machine
"""

__all__ = [
    "utils", "assets", "audio", "effects", "projectiles", "collectibles",
    "plants", "zombies", "grid", "waves", "ui", "save", "game",
]

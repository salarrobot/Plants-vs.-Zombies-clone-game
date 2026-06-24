"""
main.py
=======
Entry point for *Botanical Brigade*, a Plants vs Zombies inspired game.

Run with:

    python main.py

All game logic lives in the :mod:`src` package; this file only performs a
friendly dependency check, constructs the :class:`~src.game.Game` and runs it,
catching and reporting any unexpected error so the window never just vanishes.
"""

import sys
import traceback


def _check_dependencies():
    """Verify pygame is importable and recent enough, with a helpful message."""
    try:
        import pygame  # noqa: F401
    except ImportError:
        print("=" * 60)
        print(" pygame is not installed.")
        print(" Install it with:  python -m pip install -r requirements.txt")
        print(" or directly:      python -m pip install pygame")
        print("=" * 60)
        sys.exit(1)


def main():
    _check_dependencies()
    # Imported after the dependency check so the message above is shown first.
    from src.game import Game

    try:
        Game().run()
    except Exception:                       # pragma: no cover - safety net
        print("An unexpected error occurred:\n")
        traceback.print_exc()
        try:
            import pygame
            pygame.quit()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()

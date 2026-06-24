# 🌻 Botanical Brigade — a Plants vs. Zombies clone

A complete, polished **Plants vs. Zombies–inspired** tower-defence game written
from scratch in **Python + PyGame**, using clean object-oriented design across
multiple modules. **Every graphic and every sound is generated procedurally at
runtime** — there are no asset files to download, so the only dependency is
PyGame itself.

---

## ✨ Features

**Core gameplay**
- 5×9 grid lawn, just like the original.
- Zombies spawn from the right and march toward your house.
- **4 zombie types:** Browncoat (normal), Track Runner (fast), Buckethead
  (tank, high health) and the **Gargantuar boss**.
- **5 plant types:** Sunflower (sun), Peashooter (peas), Wall-nut (defensive
  wall), **Snow Pea** (slows enemies) and **Cherry Bomb** (area explosion).
- Sun economy: collect sun from the sky and from Sunflowers.
- Mouse-driven plant placement with a top **seed-selection bar**.
- Projectile collision, zombie eating mechanics and per-plant health.
- **Win** by surviving every wave; **lose** if a zombie gets past a spent mower.

**Advanced systems**
- **5 levels** of increasing difficulty with a **procedural wave generator** —
  no two runs are identical.
- Wave-management system with grace periods, escalating "huge" final waves and
  on-screen wave banners/meter.
- Per-plant **planting cooldowns** with an animated recharge sweep.
- Procedurally **animated** plants and zombies (walk cycles, bobs, recoil).
- **Particle effects** for explosions, hits, sun pickups and dust.
- Procedurally **synthesised sound effects + looping background music**.
- Full state machine: **Main Menu → Level Select → Play → Pause → Shop →
  Game Over / Victory**.
- **Save / load** progress, **high-score** tracking and lifetime stats.
- Health bars over every plant and zombie; live sun, score, level and wave HUD.

**Bonus features**
- **Boss zombie** (Gargantuar) on the final level.
- **Snow Pea** that slows enemies (ice mechanic).
- Procedurally generated waves.
- **Achievement system** (7 achievements with pop-up toasts).
- **Upgrade shop** between levels (sun bonus, pea power, plant armour, turbo
  mowers).
- **Lawn mowers** as a last line of defence.
- **Full-screen** support (`F11`) and **responsive UI scaling** — the game
  renders to a fixed logical canvas that is letter-boxed to any window size.

**Code quality**
- No hard-coded gameplay values — everything lives in [`config.py`](config.py).
- Clear OOP structure split across focused modules.
- Graceful error handling (missing audio device, corrupt save, etc.).
- Comfortably exceeds 60 FPS (measured ~2.5 ms/frame on a busy scene).

---

## 🛠 Requirements

- **Python 3.8+**
- **PyGame 2.0+**

## 🚀 Installation & running

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 2. install the single dependency
python -m pip install -r requirements.txt

# 3. play!
python main.py
```

> On Windows, if `python` is not recognised, use the launcher: `py main.py`.

---

## 🎮 Controls

| Action | Control |
| --- | --- |
| Select a plant | Click its card in the top bar |
| Place a plant | Click an empty lawn tile |
| Cancel selection | Right-click or `ESC` |
| Collect sun | Click the sun token |
| Dig up a plant | Select the shovel, then click the plant |
| Pause / resume | `ESC` or `P`, or the pause button |
| Mute / unmute | `M` |
| Toggle full-screen | `F11` |



---





"""
game.py
=======
The top-level :class:`Game` object: window/display management, the finite
state machine (menu / play / pause / shop / game-over / victory) and all of the
in-level orchestration that the entity classes hook into.

Rendering model
----------------
Everything is drawn onto a fixed-size *logical* canvas
(:data:`config.LOGICAL_SIZE`).  Each frame that canvas is scaled -- preserving
aspect ratio with letter-boxing -- onto the real window (or full-screen
surface).  This delivers crisp, responsive UI scaling and trivial full-screen
support, and means all gameplay maths can ignore the actual resolution.
"""

import random
import sys

import pygame

import config as C
from src import utils
from src.assets import AssetManager
from src.audio import SoundManager
from src.save import SaveManager
from src.effects import ParticleSystem
from src.grid import Grid, Mower
from src.ui import Button, SeedBar, HUD
from src.waves import WaveManager
from src.plants import create_plant
from src.zombies import create_zombie
from src.collectibles import Sun


# Game states
MENU, LEVEL_SELECT, PLAYING, PAUSED, SHOP, GAME_OVER, VICTORY, HELP = range(8)


class Game:
    """Owns the window, the state machine and the active level."""

    def __init__(self):
        pygame.init()
        # The SoundManager pre-inits the mixer; create it before the display
        # so audio is ready immediately.
        self.sound = SoundManager()

        self.fullscreen = False
        self.window_size = (C.DEFAULT_WINDOW_WIDTH, C.DEFAULT_WINDOW_HEIGHT)
        self.screen = pygame.display.set_mode(self.window_size,
                                              pygame.RESIZABLE)
        pygame.display.set_caption(C.WINDOW_TITLE)

        self.canvas = pygame.Surface(C.LOGICAL_SIZE).convert()
        self.clock = pygame.time.Clock()
        self.running = True

        self.assets = AssetManager()
        self.save = SaveManager()

        # scaling/letterbox bookkeeping (filled in by present())
        self._scale = 1.0
        self._offset = (0, 0)
        self.mouse = (0, 0)

        # in-level state (populated by load_level)
        self.particles = ParticleSystem()
        self.grid = Grid()
        self.plants = []
        self.zombies = []
        self.projectiles = []
        self.suns = []
        self.mowers = []
        self.wave_manager = None
        self.seed_bar = SeedBar()
        self.hud = HUD()

        self.level = 1
        self.sun = C.STARTING_SUN
        self.score = 0
        self.level_score = 0
        self.selected_plant = None
        self.shovel_selected = False
        self.plant_cooldowns = {k: 0.0 for k in C.PLANT_ORDER}
        self.sky_sun_timer = 0.0
        self.shake = 0.0
        self.mower_triggered_this_level = False

        self.state = MENU
        self._build_buttons()
        self.sound.start_music()

    # ===================================================================
    # Button construction (one set per menu/state)
    # ===================================================================
    def _build_buttons(self):
        cx = C.LOGICAL_WIDTH // 2
        bw, bh = 320, 64
        self.menu_buttons = [
            Button((cx - bw // 2, 330, bw, bh), "Play", action="play"),
            Button((cx - bw // 2, 406, bw, bh), "Level Select",
                   action="levelselect"),
            Button((cx - bw // 2, 482, bw, bh), "How to Play", action="help"),
            Button((cx - bw // 2, 558, bw, bh), "Quit", action="quit"),
        ]

        self.pause_buttons = [
            Button((cx - 160, 280, 320, 60), "Resume", action="resume"),
            Button((cx - 160, 350, 320, 60), "Restart Level",
                   action="restart"),
            Button((cx - 160, 420, 320, 60), "Toggle Sound", action="mute"),
            Button((cx - 160, 490, 320, 60), "Main Menu", action="menu"),
        ]

        self.gameover_buttons = [
            Button((cx - 330, 480, 300, 64), "Retry Level", action="restart"),
            Button((cx + 30, 480, 300, 64), "Main Menu", action="menu"),
        ]

        self.victory_buttons = [
            Button((cx - 330, 520, 300, 64), "Play Again", action="play"),
            Button((cx + 30, 520, 300, 64), "Main Menu", action="menu"),
        ]

        self.help_buttons = [
            Button((cx - 150, 620, 300, 60), "Back", action="menu"),
        ]

        # level-select grid
        self.level_buttons = []
        per_row = 5
        size = 150
        gap = 24
        total_w = per_row * size + (per_row - 1) * gap
        start_x = cx - total_w // 2
        for i in range(C.NUM_LEVELS):
            col = i % per_row
            bx = start_x + col * (size + gap)
            self.level_buttons.append(
                Button((bx, 320, size, size), f"{i + 1}",
                       font_size=48, action=("level", i + 1)))
        self.levelselect_back = Button((cx - 150, 560, 300, 60), "Back",
                                       action="menu")

        # shop
        self.shop_buttons = {}
        y = 230
        for key in C.SHOP_ITEMS:
            self.shop_buttons[key] = Button(
                (C.LOGICAL_WIDTH - 360, y, 180, 54), "Buy",
                font_size=26, action=("buy", key),
                base_color=(120, 190, 110))
            y += 96
        self.shop_continue = Button((cx - 160, 628, 320, 60), "Continue",
                                    action="continue")

    # ===================================================================
    # Level lifecycle
    # ===================================================================
    def start_run(self, level):
        """Begin a fresh campaign run at *level* (resets the score)."""
        self.score = 0
        self.load_level(level)

    def load_level(self, level):
        """Reset all in-level state and start *level*."""
        self.level = level
        self.particles.clear()
        self.grid.clear()
        self.plants.clear()
        self.zombies.clear()
        self.projectiles.clear()
        self.suns.clear()
        self.mowers = [Mower(r) for r in range(C.GRID_ROWS)]
        self.wave_manager = WaveManager(self, level)

        bonus = 25 * self.save.upgrade_level("sun_bonus")
        self.sun = C.STARTING_SUN + bonus
        self.level_score = 0
        self.selected_plant = None
        self.shovel_selected = False
        self.plant_cooldowns = {k: 0.0 for k in C.PLANT_ORDER}
        self.sky_sun_timer = random.uniform(C.SKY_SUN_MIN_INTERVAL,
                                            C.SKY_SUN_MAX_INTERVAL)
        self.shake = 0.0
        self.mower_triggered_this_level = False
        self.hud.toasts.clear()
        self.state = PLAYING

    def complete_level(self):
        """Handle a cleared level: rewards, achievements and next step."""
        self.sound.play("win")
        self.save.add_coins(self.level_score)
        self.save.add_stat("levels_cleared")
        if not self.mower_triggered_this_level:
            self._unlock("survivor")
        self.save.submit_score(self.score)

        if self.level >= C.NUM_LEVELS:
            self._unlock("champion")
            self.state = VICTORY
        else:
            self.save.unlock_level(self.level + 1)
            self.state = SHOP

    def trigger_game_over(self):
        self.sound.play("lose")
        self.save.submit_score(self.score)
        self.state = GAME_OVER

    # ===================================================================
    # Hooks called by entities / managers
    # ===================================================================
    def get_upgrade_level(self, key):
        return self.save.upgrade_level(key)

    def add_projectile(self, pea):
        self.projectiles.append(pea)

    def add_shake(self, amount):
        self.shake = max(self.shake, amount)

    def spawn_plant_sun(self, x, y, value):
        sun = Sun(x + random.uniform(-6, 6), y, value,
                  target_y=y + 28, from_plant=True)
        self.suns.append(sun)

    def spawn_zombie(self, key, row, health_mult, speed_mult):
        self.zombies.append(create_zombie(key, row, self, health_mult,
                                          speed_mult))

    def active_zombie_count(self):
        return sum(1 for z in self.zombies if z.alive)

    def zombie_in_row_ahead(self, row, x):
        for z in self.zombies:
            if z.alive and z.row == row and x < z.x <= C.LOGICAL_WIDTH:
                return True
        return False

    def plant_blocking(self, row, x):
        """Return the rightmost plant within eating range of a zombie at *x*."""
        best = None
        for p in self.plants:
            if p.row != row or not p.alive:
                continue
            if abs(p.x - x) <= C.CELL_W * 0.45:
                if best is None or p.x > best.x:
                    best = p
        return best

    def notify_cherry_kills(self, killed):
        if killed >= 4:
            self._unlock("boom")

    def on_wave_start(self, number, is_final):
        if is_final:
            self.hud.add_toast("FINAL WAVE!", "Hold the line!")
        elif number > 1:
            self.hud.add_toast(f"Wave {number} incoming")

    # ===================================================================
    # Achievements helper
    # ===================================================================
    def _unlock(self, key):
        if self.save.unlock_achievement(key):
            info = C.ACHIEVEMENTS[key]
            self.hud.add_toast("Achievement: " + info["name"], info["desc"])
            self.sound.play("achieve")

    def _check_stat_achievements(self):
        if self.save.stat("zombies_killed") >= 1:
            self._unlock("first_blood")
        if self.save.stat("zombies_killed") >= 100:
            self._unlock("centurion")
        if self.save.stat("plants_placed") >= 25:
            self._unlock("green_thumb")
        if self.save.stat("sun_collected") >= 1000:
            self._unlock("sun_tycoon")

    # ===================================================================
    # Main loop
    # ===================================================================
    def run(self):
        while self.running:
            dt = self.clock.tick(C.FPS) / 1000.0
            dt = min(dt, 0.05)              # clamp huge spikes (e.g. window drag)
            self.mouse = self._to_logical(pygame.mouse.get_pos())
            self._process_events()
            self._update(dt)
            self._draw()
            self._present()
        self.save.save()
        pygame.quit()

    # -- events ------------------------------------------------------------
    def _process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.window_size = (max(640, event.w), max(360, event.h))
                self.screen = pygame.display.set_mode(self.window_size,
                                                      pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = self._to_logical(event.pos)
                self._handle_click(pos, event.button)

    def _handle_keydown(self, event):
        if event.key == pygame.K_F11:
            self._toggle_fullscreen()
        elif event.key == pygame.K_m:
            self.sound.toggle_mute()
        elif event.key == pygame.K_ESCAPE:
            if self.state == PLAYING:
                self.state = PAUSED
            elif self.state == PAUSED:
                self.state = PLAYING
            elif self.state in (LEVEL_SELECT, HELP):
                self.state = MENU
        elif event.key == pygame.K_p and self.state in (PLAYING, PAUSED):
            self.state = PAUSED if self.state == PLAYING else PLAYING

    def _handle_click(self, pos, button):
        if self.state == MENU:
            self._click_buttons(self.menu_buttons, pos)
        elif self.state == LEVEL_SELECT:
            for b in self.level_buttons:
                if b.hit(pos):
                    self._do_action(b.action)
            if self.levelselect_back.hit(pos):
                self._do_action(self.levelselect_back.action)
        elif self.state == HELP:
            self._click_buttons(self.help_buttons, pos)
        elif self.state == PLAYING:
            self._click_play(pos, button)
        elif self.state == PAUSED:
            self._click_buttons(self.pause_buttons, pos)
        elif self.state == SHOP:
            self._click_shop(pos)
        elif self.state == GAME_OVER:
            self._click_buttons(self.gameover_buttons, pos)
        elif self.state == VICTORY:
            self._click_buttons(self.victory_buttons, pos)

    def _click_buttons(self, buttons, pos):
        for b in buttons:
            if b.hit(pos):
                self.sound.play("click")
                self._do_action(b.action)
                return

    def _do_action(self, action):
        if action == "play":
            self.start_run(1)
        elif action == "levelselect":
            self.state = LEVEL_SELECT
        elif action == "help":
            self.state = HELP
        elif action == "quit":
            self.running = False
        elif action == "resume":
            self.state = PLAYING
        elif action == "restart":
            self.start_run(self.level)
        elif action == "menu":
            self.state = MENU
        elif action == "mute":
            self.sound.toggle_mute()
        elif action == "continue":
            self.load_level(self.level + 1)
        elif isinstance(action, tuple):
            kind, value = action
            if kind == "level":
                if value <= self.save.highest_level:
                    self.start_run(value)
            elif kind == "buy":
                if self.save.buy_upgrade(value):
                    self.sound.play("sun")
                else:
                    self.sound.play("click")

    # -- in-play clicks ----------------------------------------------------
    def _click_play(self, pos, button):
        if button == 3:                    # right click cancels selection
            self.selected_plant = None
            self.shovel_selected = False
            return
        if button != 1:
            return

        if self.hud.pause_rect.collidepoint(pos):
            self.sound.play("click")
            self.state = PAUSED
            return

        # collect sun (topmost first)
        for sun in reversed(self.suns):
            if not sun.collected and sun.contains(*pos):
                self._collect_sun(sun)
                return

        # seed cards
        key = self.seed_bar.card_at(pos)
        if key is not None:
            self._select_card(key)
            return
        if self.seed_bar.shovel_at(pos):
            self.shovel_selected = not self.shovel_selected
            self.selected_plant = None
            self.sound.play("click")
            return

        # lawn interaction
        cell = self.grid.cell_at_pixel(*pos)
        if cell is not None:
            row, col = cell
            if self.shovel_selected:
                self._dig_plant(row, col)
            elif self.selected_plant is not None:
                self._place_plant(row, col)

    def _select_card(self, key):
        cost = C.PLANT_DATA[key]["cost"]
        if self.plant_cooldowns.get(key, 0) > 0 or self.sun < cost:
            self.sound.play("click")
            self.selected_plant = None
            return
        self.selected_plant = key
        self.shovel_selected = False
        self.sound.play("click")

    def _place_plant(self, row, col):
        key = self.selected_plant
        cost = C.PLANT_DATA[key]["cost"]
        if not self.grid.is_empty(row, col):
            self.sound.play("click")
            return
        if self.sun < cost or self.plant_cooldowns.get(key, 0) > 0:
            self.sound.play("click")
            return
        plant = create_plant(key, row, col, self)
        self.grid.place(plant)
        self.plants.append(plant)
        self.sun -= cost
        self.plant_cooldowns[key] = C.PLANT_DATA[key]["cooldown"]
        self.particles.dust(plant.x, plant.y + 20)
        self.sound.play("plant")
        self.save.add_stat("plants_placed")
        self._check_stat_achievements()
        self.selected_plant = None

    def _dig_plant(self, row, col):
        plant = self.grid.cells[row][col]
        if plant is not None:
            plant.alive = False
            self.particles.dust(plant.x, plant.y)
            self.sound.play("plant")
        self.shovel_selected = False

    def _collect_sun(self, sun):
        sun.collect()
        self.sun += sun.value
        self.particles.sun_sparkle(sun.x, sun.y)
        self.particles.floating_text(sun.x, sun.y - 10, f"+{sun.value}",
                                     (255, 230, 120))
        self.sound.play("sun")
        self.save.add_stat("sun_collected", sun.value)
        self._check_stat_achievements()

    # ===================================================================
    # Update
    # ===================================================================
    def _update(self, dt):
        # shake decays in every state
        if self.shake > 0:
            self.shake = max(0.0, self.shake - C.SCREEN_SHAKE_DECAY * dt)
        self.hud.update(dt)
        if self.state == PLAYING:
            self._update_play(dt)

    def _update_play(self, dt):
        # sky sun spawning
        self.sky_sun_timer -= dt
        if self.sky_sun_timer <= 0:
            self._spawn_sky_sun()
            self.sky_sun_timer = random.uniform(C.SKY_SUN_MIN_INTERVAL,
                                                 C.SKY_SUN_MAX_INTERVAL)

        # plant cooldowns
        for key in self.plant_cooldowns:
            if self.plant_cooldowns[key] > 0:
                self.plant_cooldowns[key] = max(
                    0.0, self.plant_cooldowns[key] - dt)

        self.wave_manager.update(dt)

        for plant in self.plants:
            plant.update(dt)
        self.plants = [p for p in self.plants if p.alive]
        self.grid.sync_dead()

        # projectiles + collision
        for pea in self.projectiles:
            pea.update(dt)
            self._resolve_pea(pea)
        self.projectiles = [p for p in self.projectiles if p.alive]

        # zombies
        for z in self.zombies:
            z.update(dt)
            if z.alive and z.x <= C.GRID_ORIGIN_X - 25:
                self._handle_breach(z)
        for z in self.zombies:
            if z.dying and not z.death_processed:
                z.death_processed = True
                self._handle_zombie_death(z)
        self.zombies = [z for z in self.zombies if not z.dead]

        # suns
        for sun in self.suns:
            sun.update(dt, hud_target=(78, 60))
        self.suns = [s for s in self.suns if s.alive]

        # mowers (the Turbo Mowers upgrade recharges a spent mower over time)
        recharge = self.save.upgrade_level("fast_mowers") > 0
        for mower in self.mowers:
            mower.update(dt, self.zombies, self.particles, self.sound)
            if recharge and mower.state == "spent":
                mower.recharge_timer += dt
                if mower.recharge_timer >= C.MOWER_RECHARGE_TIME:
                    mower.recharge()

        self.particles.update(dt)

        # win check
        if self.wave_manager.is_cleared():
            self.complete_level()

    def _spawn_sky_sun(self):
        x = random.uniform(C.GRID_ORIGIN_X + 40,
                           C.GRID_ORIGIN_X + C.GRID_WIDTH - 40)
        target = random.uniform(C.GRID_ORIGIN_Y + 50,
                                C.GRID_ORIGIN_Y + C.GRID_HEIGHT - 50)
        self.suns.append(Sun(x, C.TOP_BAR_HEIGHT, C.SKY_SUN_VALUE,
                             target_y=target))

    def _resolve_pea(self, pea):
        if not pea.alive:
            return
        target = None
        for z in self.zombies:
            if not z.alive or z.row != pea.row:
                continue
            if abs(z.x - pea.x) <= z.width * 0.34:
                if target is None or z.x < target.x:
                    target = z
        if target is not None:
            target.take_damage(pea.damage)
            if pea.frost:
                target.apply_slow(C.PLANT_DATA["icepea"]["slow_duration"])
                self.particles.hit_spark(pea.x, pea.y, (150, 210, 255))
            else:
                self.particles.hit_spark(pea.x, pea.y)
            self.sound.play("hit")
            pea.alive = False

    def _handle_breach(self, zombie):
        mower = self.mowers[zombie.row]
        if mower.state == "idle":
            mower.trigger()
            self.mower_triggered_this_level = True
            self.sound.play("mower")
        elif mower.state == "spent":
            zombie.x = C.GRID_ORIGIN_X - 25      # freeze it at the threshold
            self.trigger_game_over()

    def _handle_zombie_death(self, zombie):
        self.score += zombie.reward
        self.level_score += zombie.reward
        self.particles.burst(zombie.x, zombie.y, (120, 170, 110),
                             count=14, speed=180)
        self.sound.play("zombie_die")
        self.save.add_stat("zombies_killed")
        self._check_stat_achievements()

    # ===================================================================
    # Rendering
    # ===================================================================
    def _draw(self):
        if self.state == MENU:
            self._draw_menu()
        elif self.state == LEVEL_SELECT:
            self._draw_levelselect()
        elif self.state == HELP:
            self._draw_help()
        elif self.state in (PLAYING, PAUSED):
            self._draw_play()
            if self.state == PAUSED:
                self._draw_pause()
        elif self.state == SHOP:
            self._draw_play_background()
            self._draw_shop()
        elif self.state == GAME_OVER:
            self._draw_play()
            self._draw_gameover()
        elif self.state == VICTORY:
            self._draw_play_background()
            self._draw_victory()

    # -- shared backgrounds ------------------------------------------------
    def _draw_play_background(self):
        self.canvas.blit(self.assets.background, (0, 0))

    def _dim(self, alpha=150, color=(10, 10, 20)):
        overlay = pygame.Surface(C.LOGICAL_SIZE, pygame.SRCALPHA)
        overlay.fill((*color, alpha))
        self.canvas.blit(overlay, (0, 0))

    # -- play --------------------------------------------------------------
    def _draw_play(self):
        self.canvas.blit(self.assets.background, (0, 0))

        # placement highlight
        if (self.selected_plant or self.shovel_selected) and \
                self.state == PLAYING:
            cell = self.grid.cell_at_pixel(*self.mouse)
            if cell is not None:
                row, col = cell
                valid = self.shovel_selected or self.grid.is_empty(row, col)
                self.grid.draw_cell_highlight(self.canvas, row, col, valid)

        for mower in self.mowers:
            mower.draw(self.canvas, self.assets)

        # draw plants & zombies sorted by row so lower rows overlap correctly
        for plant in sorted(self.plants, key=lambda p: p.y):
            plant.draw(self.canvas, self.assets)
        for z in sorted(self.zombies, key=lambda z: z.y):
            z.draw(self.canvas, self.assets)

        for pea in self.projectiles:
            pea.draw(self.canvas, self.assets)
        for sun in self.suns:
            sun.draw(self.canvas, self.assets)

        self.particles.draw(self.canvas)
        self.hud.draw(self.canvas, self)

        # held-plant ghost following the cursor
        if self.selected_plant and self.state == PLAYING:
            icon = self.assets.plant(self.selected_plant)
            ghost = icon.copy()
            ghost.set_alpha(150)
            self.canvas.blit(ghost, ghost.get_rect(center=self.mouse))

        # wave banner
        if self.wave_manager and self.wave_manager.banner_timer > 0:
            self._draw_wave_banner()

    def _draw_wave_banner(self):
        text = ("FINAL WAVE!" if self.wave_manager.is_final_wave
                else f"Wave {self.wave_manager.current_wave}")
        a = min(1.0, self.wave_manager.banner_timer)
        label_color = (230, 70, 60) if self.wave_manager.is_final_wave \
            else (255, 240, 180)
        surf = utils.get_font(72, bold=True).render(text, True, label_color)
        surf.set_alpha(int(255 * a))
        rect = surf.get_rect(center=(C.LOGICAL_WIDTH // 2, 280))
        self.canvas.blit(surf, rect)

    def _draw_pause(self):
        self._dim(150)
        utils.draw_text(self.canvas, "PAUSED", 72, C.LOGICAL_WIDTH // 2, 190,
                        color=C.WHITE, center=True, bold=True)
        sound_label = "Sound: OFF" if self.sound.muted else "Sound: ON"
        self.pause_buttons[2].label = sound_label
        for b in self.pause_buttons:
            b.draw(self.canvas, self.mouse)

    # -- menu --------------------------------------------------------------
    def _draw_menu(self):
        self.canvas.blit(self.assets.background, (0, 0))
        self._dim(120, (20, 30, 50))
        # title
        self._draw_title("BOTANICAL", "BRIGADE", 130)
        utils.draw_text(self.canvas, "a Plants vs Zombies clone", 26,
                        C.LOGICAL_WIDTH // 2, 288, color=(245, 245, 245),
                        center=True, bold=True)
        for b in self.menu_buttons:
            b.draw(self.canvas, self.mouse)
        utils.draw_text(self.canvas, f"High Score: {self.save.high_score}", 26,
                        20, C.LOGICAL_HEIGHT - 40, color=C.WHITE, bold=True)
        utils.draw_text(self.canvas, f"Coins: {self.save.coins}", 26,
                        C.LOGICAL_WIDTH - 200, C.LOGICAL_HEIGHT - 40,
                        color=(255, 220, 120), bold=True)

    def _draw_title(self, line1, line2, y):
        cx = C.LOGICAL_WIDTH // 2
        font = utils.get_font(96, bold=True)
        for i, line in enumerate((line1, line2)):
            shadow = font.render(line, True, (20, 60, 20))
            label = font.render(line, True, (120, 220, 90))
            yy = y + i * 90
            self.canvas.blit(shadow, shadow.get_rect(center=(cx + 4, yy + 4)))
            self.canvas.blit(label, label.get_rect(center=(cx, yy)))

    # -- level select ------------------------------------------------------
    def _draw_levelselect(self):
        self.canvas.blit(self.assets.background, (0, 0))
        self._dim(140, (20, 30, 50))
        utils.draw_text(self.canvas, "Select a Level", 60,
                        C.LOGICAL_WIDTH // 2, 180, color=C.WHITE,
                        center=True, bold=True)
        for i, b in enumerate(self.level_buttons):
            unlocked = (i + 1) <= self.save.highest_level
            b.enabled = unlocked
            b.draw(self.canvas, self.mouse)
            name = C.LEVEL_CONFIG[i + 1]["name"]
            color = C.WHITE if unlocked else (120, 120, 120)
            utils.draw_text(self.canvas, name, 18, b.rect.centerx,
                            b.rect.bottom - 28, color=color, center=True)
            if not unlocked:
                utils.draw_text(self.canvas, "LOCKED", 16, b.rect.centerx,
                                b.rect.centery + 30, color=(200, 80, 80),
                                center=True, bold=True)
        self.levelselect_back.draw(self.canvas, self.mouse)

    # -- help --------------------------------------------------------------
    def _draw_help(self):
        self.canvas.blit(self.assets.background, (0, 0))
        self._dim(170, (15, 20, 35))
        cx = C.LOGICAL_WIDTH // 2
        utils.draw_text(self.canvas, "How to Play", 60, cx, 90,
                        color=C.WHITE, center=True, bold=True)
        lines = [
            "Goal: stop the zombies from reaching your house on the left.",
            "Collect SUN (falling from the sky or made by Sunflowers).",
            "Click a seed card at the top, then click a lawn tile to plant.",
            "Right-click or press ESC to cancel a selection.",
            "Use the shovel to dig up a plant you no longer want.",
            "",
            "Plants:",
            "  Sunflower  - produces extra sun.",
            "  Peashooter - fires peas at zombies in its row.",
            "  Wall-nut   - tough wall that blocks zombies.",
            "  Snow Pea   - peas that slow zombies down.",
            "  Cherry Bomb- explodes, clearing nearby zombies.",
            "",
            "Survive every wave to win. A zombie past a spent mower = game over.",
            "Earn coins to buy upgrades in the shop between levels.",
            "",
            "Keys:  ESC/P pause   M mute   F11 full-screen",
        ]
        y = 160
        for line in lines:
            utils.draw_text(self.canvas, line, 26, cx - 440, y,
                            color=(235, 235, 235))
            y += 30
        for b in self.help_buttons:
            b.draw(self.canvas, self.mouse)

    # -- shop --------------------------------------------------------------
    def _draw_shop(self):
        self._dim(170, (15, 25, 40))
        cx = C.LOGICAL_WIDTH // 2
        utils.draw_text(self.canvas, "Upgrade Shop", 58, cx, 90,
                        color=C.WHITE, center=True, bold=True)
        utils.draw_text(self.canvas, f"Coins: {self.save.coins}", 34, cx, 150,
                        color=(255, 220, 120), center=True, bold=True)

        y = 220
        for key, item in C.SHOP_ITEMS.items():
            lvl = self.save.upgrade_level(key)
            maxed = lvl >= item["max_level"]
            panel = pygame.Rect(C.LOGICAL_WIDTH // 2 - 480, y, 840, 78)
            pygame.draw.rect(self.canvas, C.UI_PANEL, panel, border_radius=12)
            pygame.draw.rect(self.canvas, utils.darken(C.UI_PANEL_DARK, 0.1),
                             panel, width=3, border_radius=12)
            utils.draw_text(self.canvas, item["name"], 28, panel.x + 18,
                            panel.y + 10, color=C.UI_TEXT, bold=True,
                            shadow=False)
            utils.draw_text(self.canvas, item["desc"], 20, panel.x + 18,
                            panel.y + 44, color=(80, 60, 40), shadow=False)
            utils.draw_text(self.canvas, f"Lv {lvl}/{item['max_level']}", 24,
                            panel.x + 540, panel.y + 26, color=C.UI_TEXT,
                            bold=True, shadow=False)
            btn = self.shop_buttons[key]
            if maxed:
                btn.label = "MAXED"
                btn.enabled = False
            else:
                btn.label = f"Buy ({item['cost']})"
                btn.enabled = self.save.coins >= item["cost"]
            btn.rect.topleft = (panel.right - 196, panel.y + 12)
            btn.draw(self.canvas, self.mouse)
            y += 96

        self.shop_continue.draw(self.canvas, self.mouse)

    def _click_shop(self, pos):
        for key, btn in self.shop_buttons.items():
            if btn.hit(pos):
                self._do_action(("buy", key))
                return
        if self.shop_continue.hit(pos):
            self.sound.play("click")
            self._do_action("continue")

    # -- game over / victory ----------------------------------------------
    def _draw_gameover(self):
        self._dim(170, (40, 10, 10))
        cx = C.LOGICAL_WIDTH // 2
        utils.draw_text(self.canvas, "THE ZOMBIES ATE", 64, cx, 200,
                        color=(230, 80, 70), center=True, bold=True)
        utils.draw_text(self.canvas, "YOUR BRAINS!", 64, cx, 270,
                        color=(230, 80, 70), center=True, bold=True)
        utils.draw_text(self.canvas, f"Score: {self.score}", 36, cx, 360,
                        color=C.WHITE, center=True, bold=True)
        utils.draw_text(self.canvas, f"High Score: {self.save.high_score}", 28,
                        cx, 410, color=(255, 220, 120), center=True)
        for b in self.gameover_buttons:
            b.draw(self.canvas, self.mouse)

    def _draw_victory(self):
        self._dim(160, (10, 40, 20))
        cx = C.LOGICAL_WIDTH // 2
        is_campaign_end = self.level >= C.NUM_LEVELS
        title = "YOU WIN!" if not is_campaign_end else "CAMPAIGN COMPLETE!"
        utils.draw_text(self.canvas, title, 70, cx, 200,
                        color=(140, 240, 110), center=True, bold=True)
        utils.draw_text(self.canvas, "Every wave defeated. The lawn is safe!",
                        30, cx, 290, color=C.WHITE, center=True)
        utils.draw_text(self.canvas, f"Final Score: {self.score}", 38, cx, 360,
                        color=C.WHITE, center=True, bold=True)
        new_hs = self.score >= self.save.high_score
        if new_hs:
            utils.draw_text(self.canvas, "NEW HIGH SCORE!", 30, cx, 410,
                            color=(255, 220, 120), center=True, bold=True)
        for b in self.victory_buttons:
            b.draw(self.canvas, self.mouse)

    # ===================================================================
    # Display scaling / presentation
    # ===================================================================
    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            info = pygame.display.Info()
            self.window_size = (info.current_w, info.current_h)
            self.screen = pygame.display.set_mode(self.window_size,
                                                  pygame.FULLSCREEN)
        else:
            self.window_size = (C.DEFAULT_WINDOW_WIDTH, C.DEFAULT_WINDOW_HEIGHT)
            self.screen = pygame.display.set_mode(self.window_size,
                                                  pygame.RESIZABLE)

    def _present(self):
        win_w, win_h = self.screen.get_size()
        scale = min(win_w / C.LOGICAL_WIDTH, win_h / C.LOGICAL_HEIGHT)
        disp_w = max(1, int(C.LOGICAL_WIDTH * scale))
        disp_h = max(1, int(C.LOGICAL_HEIGHT * scale))
        off_x = (win_w - disp_w) // 2
        off_y = (win_h - disp_h) // 2
        self._scale = scale
        self._offset = (off_x, off_y)

        # screen-shake offset
        sx = sy = 0
        if self.shake > 0:
            sx = random.uniform(-self.shake, self.shake)
            sy = random.uniform(-self.shake, self.shake)

        self.screen.fill((0, 0, 0))
        if disp_w == C.LOGICAL_WIDTH and disp_h == C.LOGICAL_HEIGHT:
            self.screen.blit(self.canvas, (off_x + sx, off_y + sy))
        else:
            scaled = pygame.transform.smoothscale(self.canvas,
                                                  (disp_w, disp_h))
            self.screen.blit(scaled, (off_x + sx, off_y + sy))
        pygame.display.flip()

    def _to_logical(self, pos):
        """Convert a window-space point to logical-canvas coordinates."""
        x = (pos[0] - self._offset[0]) / self._scale if self._scale else 0
        y = (pos[1] - self._offset[1]) / self._scale if self._scale else 0
        x = utils.clamp(x, 0, C.LOGICAL_WIDTH - 1)
        y = utils.clamp(y, 0, C.LOGICAL_HEIGHT - 1)
        return (x, y)

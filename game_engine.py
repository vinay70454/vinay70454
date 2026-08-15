"""Game engine and gameplay canvas renderer for Cosmic Defender.
Handles high-performance 60 FPS update loops, touch input, collision detection,
wave progression, power-ups, and OpenGL vector rendering.
"""

import math
import random
import time

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import (
    Color, Ellipse, Line, Mesh, PushMatrix, PopMatrix,
    Rectangle, Rotate, SmoothLine, Translate
)
from kivy.metrics import dp
from kivy.uix.widget import Widget

from audio_synth import audio_manager
from particle_system import ParallaxStarfield, ParticleSystem
from storage import SHIP_CATALOG, storage


class Bullet:
    """Player or enemy projectile."""
    def __init__(self, x, y, vx, vy, damage=25, is_player=True, bullet_type="laser", color=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.damage = damage
        self.is_player = is_player
        self.bullet_type = bullet_type
        self.radius = 4 if is_player else 5
        self.alive = True
        self.color = color or ((0.2, 0.9, 1.0, 1.0) if is_player else (1.0, 0.2, 0.3, 1.0))

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt


class PowerUp:
    """Collectible drop from destroyed hazards or enemies."""
    TYPES = ["shield", "spread", "rapid", "bomb", "repair", "coin"]

    def __init__(self, x, y, p_type=None):
        self.x = x
        self.y = y
        self.p_type = p_type or random.choices(
            ["coin", "repair", "shield", "spread", "rapid", "bomb"],
            weights=[0.45, 0.18, 0.15, 0.10, 0.08, 0.04]
        )[0]
        self.radius = 16
        self.alive = True
        self.vy = -120
        self.angle = 0
        self.pulse = 0

    def update(self, dt):
        self.y += self.vy * dt
        self.angle = (self.angle + 120 * dt) % 360
        self.pulse = (self.pulse + 4.0 * dt) % (2 * math.pi)


class Enemy:
    """Base hazard and enemy combatant."""
    def __init__(self, x, y, enemy_type="asteroid", wave=1):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.wave = wave
        self.alive = True
        self.angle = 0
        self.rotation_speed = random.uniform(-60, 60)
        self.time_alive = 0.0
        self.fire_cooldown = random.uniform(1.2, 2.5)

        # Scale stats by wave and enemy type
        if enemy_type == "asteroid":
            self.radius = random.uniform(20, 36)
            self.max_health = 30 + wave * 6
            self.health = self.max_health
            self.vx = random.uniform(-30, 30)
            self.vy = -random.uniform(120, 200) - wave * 5
            self.score_value = 50
            self.color = (0.7, 0.65, 0.6, 1.0)
            self.can_split = self.radius > 26

        elif enemy_type == "scout":
            self.radius = 18
            self.max_health = 45 + wave * 8
            self.health = self.max_health
            self.vx = random.uniform(-50, 50)
            self.vy = -random.uniform(180, 240) - wave * 8
            self.base_x = x
            self.score_value = 100
            self.color = (0.9, 0.2, 0.8, 1.0)
            self.can_split = False

        elif enemy_type == "cruiser":
            self.radius = 28
            self.max_health = 130 + wave * 22
            self.health = self.max_health
            self.vx = random.uniform(-20, 20)
            self.vy = -random.uniform(70, 110)
            self.score_value = 250
            self.color = (1.0, 0.35, 0.1, 1.0)
            self.can_split = False

        elif enemy_type == "boss":
            self.radius = 55
            self.max_health = 600 + wave * 180
            self.health = self.max_health
            self.vx = 80
            self.vy = 0
            self.target_y = 0  # set upon spawn
            self.score_value = 1500
            self.color = (1.0, 0.1, 0.2, 1.0)
            self.can_split = False
            self.is_boss = True
            self.entering = True

    def update(self, dt, target_player_pos=None):
        self.time_alive += dt
        self.angle = (self.angle + self.rotation_speed * dt) % 360

        if self.enemy_type == "asteroid":
            self.x += self.vx * dt
            self.y += self.vy * dt

        elif self.enemy_type == "scout":
            # Sinusoidal zigzag path
            self.x = self.base_x + math.sin(self.time_alive * 3.5) * 65
            self.y += self.vy * dt

        elif self.enemy_type == "cruiser":
            self.x += self.vx * dt
            self.y += self.vy * dt

        elif self.enemy_type == "boss":
            if self.entering:
                self.y -= 120 * dt
                if self.y <= self.target_y:
                    self.y = self.target_y
                    self.entering = False
            else:
                self.x += self.vx * dt
                # Hover in place at upper screen
                self.y = self.target_y + math.sin(self.time_alive * 2.0) * 15


class PlayerShip:
    """Player-controlled starfighter."""
    def __init__(self, ship_id="interceptor"):
        self.ship_id = ship_id
        config = SHIP_CATALOG.get(ship_id, SHIP_CATALOG["interceptor"])

        # Upgrades
        fire_lvl = storage.get_upgrade_level(ship_id, "fire_rate")
        laser_lvl = storage.get_upgrade_level(ship_id, "laser_power")
        shield_lvl = storage.get_upgrade_level(ship_id, "shield_capacity")
        speed_lvl = storage.get_upgrade_level(ship_id, "speed")

        self.max_health = config["base_health"] + (shield_lvl - 1) * 20
        self.health = self.max_health
        self.max_shield = 60 + (shield_lvl - 1) * 25
        self.shield = self.max_shield
        self.shield_regen_rate = 12  # hp per sec
        self.fire_rate = config["base_fire_rate"] + (fire_lvl - 1) * 0.8
        self.laser_damage = 25 + (laser_lvl - 1) * 8
        self.speed = config["base_speed"] + (speed_lvl - 1) * 35

        self.x = 400
        self.y = 120
        self.target_x = 400
        self.target_y = 120
        self.radius = 22
        self.color = config["color"]

        # Buffs / Timers
        self.fire_timer = 0.0
        self.rapid_fire_time = 0.0
        self.spread_fire_time = 0.0
        self.invulnerable_time = 1.5  # brief spawn immunity
        self.bombs_count = 1

    def update(self, dt):
        # Smooth interpolation to target position for silky touch feel
        lerp_speed = 18.0
        self.x += (self.target_x - self.x) * min(1.0, dt * lerp_speed)
        self.y += (self.target_y - self.y) * min(1.0, dt * lerp_speed)

        # Timers
        if self.fire_timer > 0:
            self.fire_timer -= dt
        if self.rapid_fire_time > 0:
            self.rapid_fire_time -= dt
        if self.spread_fire_time > 0:
            self.spread_fire_time -= dt
        if self.invulnerable_time > 0:
            self.invulnerable_time -= dt

        # Shield passive regeneration
        if self.shield < self.max_shield and self.health > 0:
            self.shield = min(self.max_shield, self.shield + self.shield_regen_rate * dt)

    def take_damage(self, damage):
        """Take hit, shielding absorbs first."""
        if self.invulnerable_time > 0:
            return False

        if self.shield > 0:
            if self.shield >= damage:
                self.shield -= damage
                damage = 0
            else:
                damage -= self.shield
                self.shield = 0

        if damage > 0:
            self.health = max(0, self.health - damage)

        audio_manager.play("hit")
        return True


class CosmicGameWidget(Widget):
    """Primary game canvas and simulation engine."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.starfield = ParallaxStarfield(width=800, height=600)
        self.particles = ParticleSystem()

        self.player = None
        self.bullets = []
        self.enemies = []
        self.powerups = []

        self.score = 0
        self.coins_this_run = 0
        self.wave = 1
        self.enemies_killed = 0
        self.boss_active = False
        self.boss_killed = False

        self.is_playing = False
        self.is_paused = False
        self.auto_fire = True
        self.touch_active = False

        self.spawn_timer = 0.0
        self.wave_timer = 0.0
        self.wave_banner_time = 2.5
        self.wave_banner_text = "WAVE 1"

        # Touch tracking
        self.touch_id = None
        self.touch_offset_y = dp(55)

        self.bind(size=self._on_size_change)
        Clock.schedule_interval(self.game_loop, 1.0 / 60.0)

    def _on_size_change(self, *args):
        self.starfield.resize(self.width, self.height)

    def start_game(self, ship_id=None):
        """Reset and launch a new game session."""
        selected_ship = ship_id or storage.get_selected_ship()
        self.player = PlayerShip(selected_ship)
        self.player.x = self.width / 2 if self.width > 0 else 400
        self.player.y = dp(100)
        self.player.target_x = self.player.x
        self.player.target_y = self.player.y

        self.bullets.clear()
        self.enemies.clear()
        self.powerups.clear()

        self.score = 0
        self.coins_this_run = 0
        self.wave = 1
        self.enemies_killed = 0
        self.boss_active = False
        self.boss_killed = False
        self.spawn_timer = 0.8
        self.wave_timer = 0.0
        self.wave_banner_time = 2.5
        self.wave_banner_text = "WAVE 1 - ENGAGE"

        self.is_playing = True
        self.is_paused = False

    def pause_game(self):
        self.is_paused = True

    def resume_game(self):
        self.is_paused = False

    # Touch and Gestures (Android / Mouse)
    def on_touch_down(self, touch):
        if not self.is_playing or self.is_paused:
            return super().on_touch_down(touch)

        # Check EMP Bomb trigger button area (bottom right)
        bomb_btn_x = self.width - dp(65)
        bomb_btn_y = dp(65)
        if math.hypot(touch.x - bomb_btn_x, touch.y - bomb_btn_y) <= dp(35):
            self.trigger_emp_bomb()
            return True

        # Check Pause button area (top right)
        if touch.x >= self.width - dp(60) and touch.y >= self.height - dp(60):
            # Handled by UI overlay
            return super().on_touch_down(touch)

        self.touch_active = True
        self.touch_id = touch.id
        self._update_player_target(touch.x, touch.y)
        return True

    def on_touch_move(self, touch):
        if not self.is_playing or self.is_paused:
            return super().on_touch_move(touch)
        if self.touch_id == touch.id or self.touch_id is None:
            self._update_player_target(touch.x, touch.y)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.touch_id == touch.id:
            self.touch_id = None
            self.touch_active = False
            return True
        return super().on_touch_up(touch)

    def _update_player_target(self, x, y):
        if not self.player:
            return
        # Position ship above the user's thumb so it is never obscured
        clamped_x = max(self.player.radius, min(self.width - self.player.radius, x))
        clamped_y = max(self.player.radius, min(self.height - self.player.radius, y + self.touch_offset_y))
        self.player.target_x = clamped_x
        self.player.target_y = clamped_y

    def trigger_emp_bomb(self):
        """Activate screen-clearing EMP bomb."""
        if not self.player or self.player.bombs_count <= 0 or not self.is_playing or self.is_paused:
            return
        self.player.bombs_count -= 1
        audio_manager.play("bomb")
        self.particles.emit_emp_shockwave(self.player.x, self.player.y, max_radius=max(self.width, self.height) * 0.9)

        # Obliterate non-boss enemies and deal massive damage to boss
        for e in self.enemies:
            if getattr(e, 'is_boss', False):
                e.health -= 350
                if e.health <= 0:
                    e.alive = False
            else:
                e.alive = False
                self.particles.emit_explosion(e.x, e.y, count=18, color_theme="plasma")
                self.score += e.score_value
                self.enemies_killed += 1

        self.particles.add_floating_text("EMP BLAST!", self.player.x, self.player.y + 40, (0.3, 0.9, 1.0, 1.0), size=24)

    # Core 60 FPS Game Loop
    def game_loop(self, dt):
        # Cap dt to avoid delta jumps on hitch
        dt = min(0.05, dt)

        # Starfield always animates
        self.starfield.update(dt)
        self.particles.update(dt)

        if not self.is_playing or self.is_paused or not self.player:
            self._render_canvas()
            return

        # Player update
        self.player.update(dt)
        self.particles.emit_thruster(self.player.x, self.player.y - self.player.radius * 0.8)

        # Player auto-firing
        eff_fire_rate = self.player.fire_rate * (2.0 if self.player.rapid_fire_time > 0 else 1.0)
        cooldown = 1.0 / max(1.0, eff_fire_rate)
        if self.player.fire_timer <= 0:
            self._fire_player_weapons()
            self.player.fire_timer = cooldown

        # Update Wave & Spawning
        self._update_spawner(dt)

        # Update Projectiles
        for b in self.bullets:
            b.update(dt)
            # Screen culling
            if b.y > self.height + 50 or b.y < -50 or b.x < -50 or b.x > self.width + 50:
                b.alive = False

        # Update Enemies
        for e in self.enemies:
            e.update(dt, (self.player.x, self.player.y))
            # Boss boundary bounce
            if getattr(e, 'is_boss', False):
                if e.x <= e.radius + dp(10) or e.x >= self.width - e.radius - dp(10):
                    e.vx = -e.vx

            # Enemy firing logic
            if e.enemy_type in ["cruiser", "boss"]:
                e.fire_cooldown -= dt
                if e.fire_cooldown <= 0:
                    self._fire_enemy_weapons(e)
                    e.fire_cooldown = random.uniform(1.4, 2.8) if e.enemy_type == "cruiser" else 0.9

            if e.y < -80:
                e.alive = False

        # Update Powerups
        for p in self.powerups:
            p.update(dt)
            if p.y < -50:
                p.alive = False

        # Collisions
        self._check_collisions()

        # Clean dead objects
        self.bullets = [b for b in self.bullets if b.alive]
        self.enemies = [e for e in self.enemies if e.alive]
        self.powerups = [p for p in self.powerups if p.alive]

        # Check Player Death / Game Over
        if self.player.health <= 0:
            self._trigger_game_over()

        # Render everything
        self._render_canvas()

    def _fire_player_weapons(self):
        audio_manager.play("laser")
        dmg = self.player.laser_damage
        speed = 700

        # Spread fire power-up or Vanguard ship feature
        if self.player.spread_fire_time > 0 or self.player.ship_id == "vanguard":
            self.bullets.append(Bullet(self.player.x, self.player.y + 15, 0, speed, damage=dmg))
            self.bullets.append(Bullet(self.player.x - 12, self.player.y + 10, -150, speed * 0.95, damage=dmg * 0.85))
            self.bullets.append(Bullet(self.player.x + 12, self.player.y + 10, 150, speed * 0.95, damage=dmg * 0.85))
        elif self.player.ship_id == "dreadnought":
            # Twin heavy laser cannons
            self.bullets.append(Bullet(self.player.x - 14, self.player.y + 15, 0, speed * 1.1, damage=dmg * 1.1, bullet_type="plasma"))
            self.bullets.append(Bullet(self.player.x + 14, self.player.y + 15, 0, speed * 1.1, damage=dmg * 1.1, bullet_type="plasma"))
        else:
            # Dual blasters
            self.bullets.append(Bullet(self.player.x - 8, self.player.y + 15, 0, speed, damage=dmg))
            self.bullets.append(Bullet(self.player.x + 8, self.player.y + 15, 0, speed, damage=dmg))

    def _fire_enemy_weapons(self, enemy):
        if getattr(enemy, 'is_boss', False):
            # Boss triple burst
            speed = 280
            for vx in [-90, 0, 90]:
                self.bullets.append(Bullet(enemy.x, enemy.y - enemy.radius, vx, -speed, damage=20, is_player=False, color=(1.0, 0.1, 0.4, 1.0)))
        else:
            # Cruiser single aimed shot
            angle = math.atan2(self.player.y - enemy.y, self.player.x - enemy.x)
            speed = 250
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.bullets.append(Bullet(enemy.x, enemy.y - enemy.radius, vx, vy, damage=15, is_player=False, color=(1.0, 0.5, 0.1, 1.0)))

    def _update_spawner(self, dt):
        self.wave_timer += dt
        if self.wave_banner_time > 0:
            self.wave_banner_time -= dt

        # Spawn Boss every 4 waves or 1500 points
        if self.wave % 4 == 0 and not self.boss_active and not self.boss_killed:
            self.boss_active = True
            boss = Enemy(self.width / 2, self.height + 80, enemy_type="boss", wave=self.wave)
            boss.target_y = self.height - dp(120)
            self.enemies.append(boss)
            self.wave_banner_text = f"WARNING: DREADNOUGHT BOSS DETECTED"
            self.wave_banner_time = 3.0
            return

        self.spawn_timer -= dt
        if self.spawn_timer <= 0 and not self.boss_active:
            # Spawn random hazard/enemy
            spawn_x = random.uniform(dp(30), max(dp(100), self.width - dp(30)))
            spawn_y = self.height + dp(40)

            weights = [0.55, 0.30, 0.15] if self.wave > 2 else [0.75, 0.25, 0.0]
            choice = random.choices(["asteroid", "scout", "cruiser"], weights=weights)[0]
            self.enemies.append(Enemy(spawn_x, spawn_y, enemy_type=choice, wave=self.wave))

            # Dynamic spawn interval scaling with wave
            base_interval = max(0.45, 1.4 - (self.wave * 0.08))
            self.spawn_timer = random.uniform(base_interval * 0.7, base_interval * 1.3)

        # Wave completion check (every 25 seconds of survival or defeating boss)
        if self.wave_timer >= 28.0 and not self.boss_active:
            self.wave += 1
            self.wave_timer = 0.0
            self.boss_killed = False
            self.wave_banner_text = f"WAVE {self.wave} - SECTOR CLEAR"
            self.wave_banner_time = 2.5
            self.particles.add_floating_text(f"WAVE {self.wave} REACHED!", self.width / 2, self.height / 2, (0.2, 1.0, 0.4, 1.0), size=24)

    def _check_collisions(self):
        # 1. Player Bullets vs Enemies
        for b in self.bullets:
            if not b.is_player or not b.alive:
                continue
            for e in self.enemies:
                if not e.alive:
                    continue
                dist = math.hypot(b.x - e.x, b.y - e.y)
                if dist <= e.radius + b.radius:
                    b.alive = False
                    e.health -= b.damage
                    self.particles.emit_explosion(b.x, b.y, count=6, color_theme="plasma", scale=0.6)

                    if e.health <= 0:
                        self._destroy_enemy(e)
                    break

        # 2. Enemy Bullets vs Player
        for b in self.bullets:
            if b.is_player or not b.alive:
                continue
            dist = math.hypot(b.x - self.player.x, b.y - self.player.y)
            if dist <= self.player.radius + b.radius:
                b.alive = False
                self.player.take_damage(b.damage)
                self.particles.trigger_shake(intensity=7.0, duration=0.2)
                self.particles.emit_explosion(self.player.x, self.player.y, count=8, color_theme="fire", scale=0.8)

        # 3. Player Ship vs Enemies (Crash / Ramming)
        for e in self.enemies:
            if not e.alive:
                continue
            dist = math.hypot(self.player.x - e.x, self.player.y - e.y)
            if dist <= self.player.radius + e.radius:
                if not getattr(e, 'is_boss', False):
                    e.alive = False
                    self._destroy_enemy(e, was_rammed=True)
                self.player.take_damage(35)
                self.particles.trigger_shake(intensity=12.0, duration=0.3)

        # 4. Player vs PowerUps
        for p in self.powerups:
            if not p.alive:
                continue
            dist = math.hypot(self.player.x - p.x, self.player.y - p.y)
            if dist <= self.player.radius + p.radius:
                p.alive = False
                self._collect_powerup(p)

    def _destroy_enemy(self, enemy, was_rammed=False):
        enemy.alive = False
        self.enemies_killed += 1
        self.score += enemy.score_value
        audio_manager.play("explosion")

        # Visual explosion
        theme = "plasma" if getattr(enemy, 'is_boss', False) else ("asteroid" if enemy.enemy_type == "asteroid" else "fire")
        scale = 2.2 if getattr(enemy, 'is_boss', False) else (1.2 if enemy.enemy_type == "cruiser" else 0.9)
        self.particles.emit_explosion(enemy.x, enemy.y, count=30, color_theme=theme, scale=scale)
        self.particles.trigger_shake(intensity=8.0 * scale, duration=0.25)

        # Asteroid splitting into 2 smaller fragments
        if enemy.enemy_type == "asteroid" and enemy.can_split:
            for angle_offset in [-40, 40]:
                frag = Enemy(enemy.x, enemy.y, enemy_type="asteroid", wave=self.wave)
                frag.radius = enemy.radius * 0.55
                frag.health = enemy.max_health * 0.4
                frag.can_split = False
                rad = math.radians(angle_offset)
                frag.vx = enemy.vx + math.sin(rad) * 90
                frag.vy = enemy.vy * 1.15
                self.enemies.append(frag)

        # Boss defeat bonus
        if getattr(enemy, 'is_boss', False):
            self.boss_active = False
            self.boss_killed = True
            self.wave_banner_text = "BOSS DESTROYED! +1500 PTS"
            self.wave_banner_time = 3.5
            self.particles.add_floating_text("BOSS DEFEATED!", self.width / 2, self.height / 2, (1.0, 0.8, 0.1, 1.0), size=28)
            for _ in range(8):
                self.powerups.append(PowerUp(enemy.x + random.uniform(-40, 40), enemy.y + random.uniform(-20, 20), p_type="coin"))
            self.powerups.append(PowerUp(enemy.x, enemy.y, p_type="bomb"))
            return

        # Chance to drop power-up or coin
        drop_chance = 0.35
        if random.random() < drop_chance:
            self.powerups.append(PowerUp(enemy.x, enemy.y))

    def _collect_powerup(self, powerup):
        audio_manager.play("pickup")
        p = powerup.p_type
        if p == "coin":
            self.coins_this_run += 1
            storage.add_coins(1)
            self.particles.add_floating_text("+1 COIN", self.player.x, self.player.y + 25, (1.0, 0.85, 0.1, 1.0))
        elif p == "shield":
            self.player.shield = self.player.max_shield
            audio_manager.play("shield")
            self.particles.add_floating_text("SHIELD RECHARGED", self.player.x, self.player.y + 25, (0.2, 0.8, 1.0, 1.0))
        elif p == "spread":
            self.player.spread_fire_time = 10.0
            self.particles.add_floating_text("SPREAD CANNON!", self.player.x, self.player.y + 25, (1.0, 0.5, 0.1, 1.0))
        elif p == "rapid":
            self.player.rapid_fire_time = 8.0
            self.particles.add_floating_text("RAPID FIRE!", self.player.x, self.player.y + 25, (1.0, 0.2, 0.2, 1.0))
        elif p == "bomb":
            self.player.bombs_count = min(3, self.player.bombs_count + 1)
            self.particles.add_floating_text("+1 EMP BOMB", self.player.x, self.player.y + 25, (0.4, 0.9, 1.0, 1.0))
        elif p == "repair":
            self.player.health = min(self.player.max_health, self.player.health + self.player.max_health * 0.4)
            self.particles.add_floating_text("HULL REPAIRED", self.player.x, self.player.y + 25, (0.2, 1.0, 0.4, 1.0))

    def _trigger_game_over(self):
        self.is_playing = False
        audio_manager.play("explosion")
        self.particles.emit_explosion(self.player.x, self.player.y, count=50, color_theme="fire", scale=2.0)
        self.particles.trigger_shake(intensity=18.0, duration=0.5)
        storage.record_game_end(self.score, self.wave, self.enemies_killed, self.boss_killed)

        # Notify parent screen / manager
        if hasattr(self, 'on_game_over_callback') and self.on_game_over_callback:
            self.on_game_over_callback(self.score, self.wave, self.coins_this_run, self.enemies_killed)

    # OpenGL Vector Canvas Rendering
    def _render_canvas(self):
        self.canvas.clear()
        with self.canvas:
            # 1. Screen Shake & Viewport Transform
            PushMatrix()
            ox, oy = self.particles.shake_offset
            Translate(ox, oy, 0)

            # 2. Deep Space Background
            Color(0.04, 0.05, 0.09, 1.0)
            Rectangle(pos=(0, 0), size=self.size)

            # 3. Parallax Stars
            for s in self.starfield.stars:
                alpha = s.brightness * (0.8 + 0.2 * math.sin(s.twinkle_phase))
                Color(0.85, 0.9, 1.0, alpha)
                Ellipse(pos=(s.x - s.size / 2, s.y - s.size / 2), size=(s.size, s.size))

            # 4. Particles & Shockwaves
            for sw in self.particles.shockwaves:
                Color(*sw.color)
                Line(circle=(sw.x, sw.y, sw.current_radius), width=2.5)

            for p in self.particles.particles:
                Color(p.r, p.g, p.b, p.a)
                Ellipse(pos=(p.x - p.size / 2, p.y - p.size / 2), size=(p.size, p.size))

            # 5. Power-ups
            for pu in self.powerups:
                # Outer pulsating glow
                glow_r = pu.radius + 3 * math.sin(pu.pulse)
                if pu.p_type == "coin":
                    Color(1.0, 0.85, 0.1, 0.9)
                elif pu.p_type == "shield":
                    Color(0.2, 0.8, 1.0, 0.9)
                elif pu.p_type == "bomb":
                    Color(0.4, 0.9, 1.0, 0.9)
                elif pu.p_type == "repair":
                    Color(0.2, 1.0, 0.4, 0.9)
                else:
                    Color(1.0, 0.5, 0.1, 0.9)

                Ellipse(pos=(pu.x - glow_r, pu.y - glow_r), size=(glow_r * 2, glow_r * 2))
                Color(1.0, 1.0, 1.0, 0.8)
                Line(circle=(pu.x, pu.y, glow_r), width=1.5)

            # 6. Enemies & Hazards
            for e in self.enemies:
                if getattr(e, 'is_boss', False):
                    # Boss Mothership
                    Color(1.0, 0.15, 0.2, 1.0)
                    Ellipse(pos=(e.x - e.radius, e.y - e.radius * 0.7), size=(e.radius * 2, e.radius * 1.4))
                    Color(0.3, 0.05, 0.1, 1.0)
                    Ellipse(pos=(e.x - e.radius * 0.6, e.y - e.radius * 0.4), size=(e.radius * 1.2, e.radius * 0.8))
                    Color(1.0, 0.8, 0.2, 0.9)
                    Line(circle=(e.x, e.y, e.radius), width=2.0)

                    # Boss Health Bar
                    bar_w = self.width * 0.7
                    bar_h = dp(8)
                    bar_x = (self.width - bar_w) / 2
                    bar_y = self.height - dp(45)
                    Color(0.2, 0.2, 0.2, 0.8)
                    Rectangle(pos=(bar_x, bar_y), size=(bar_w, bar_h))
                    Color(1.0, 0.2, 0.2, 1.0)
                    fill_w = max(0, (e.health / e.max_health) * bar_w)
                    Rectangle(pos=(bar_x, bar_y), size=(fill_w, bar_h))

                elif e.enemy_type == "asteroid":
                    # Tumbling Asteroid Rock
                    PushMatrix()
                    Translate(e.x, e.y, 0)
                    Rotate(angle=e.angle, axis=(0, 0, 1))
                    Color(*e.color)
                    Ellipse(pos=(-e.radius, -e.radius), size=(e.radius * 2, e.radius * 2))
                    Color(0.4, 0.35, 0.3, 0.9)
                    Ellipse(pos=(-e.radius * 0.4, -e.radius * 0.3), size=(e.radius * 0.6, e.radius * 0.5))
                    PopMatrix()

                elif e.enemy_type == "scout":
                    # Sleek triangular fighter
                    Color(*e.color)
                    PushMatrix()
                    Translate(e.x, e.y, 0)
                    Mesh(
                        vertices=[
                            0, -e.radius * 1.1, 0, 0,
                            -e.radius * 0.8, e.radius * 0.9, 0, 0,
                            e.radius * 0.8, e.radius * 0.9, 0, 0
                        ],
                        indices=[0, 1, 2],
                        mode='triangles'
                    )
                    PopMatrix()

                elif e.enemy_type == "cruiser":
                    # Armored heavy cruiser
                    Color(*e.color)
                    Rectangle(pos=(e.x - e.radius, e.y - e.radius * 0.7), size=(e.radius * 2, e.radius * 1.4))
                    Color(0.2, 0.1, 0.05, 1.0)
                    Line(rectangle=(e.x - e.radius, e.y - e.radius * 0.7, e.radius * 2, e.radius * 1.4), width=1.5)

            # 7. Bullets
            for b in self.bullets:
                Color(*b.color)
                if b.bullet_type == "plasma":
                    Ellipse(pos=(b.x - b.radius * 1.4, b.y - b.radius * 1.4), size=(b.radius * 2.8, b.radius * 2.8))
                else:
                    Ellipse(pos=(b.x - b.radius, b.y - b.radius * 1.6), size=(b.radius * 2, b.radius * 3.2))

            # 8. Player Starship
            if self.player and self.player.health > 0:
                # Blink if invulnerable
                if self.player.invulnerable_time <= 0 or int(self.player.invulnerable_time * 10) % 2 == 0:
                    PushMatrix()
                    Translate(self.player.x, self.player.y, 0)
                    # Hull
                    Color(*self.player.color)
                    r = self.player.radius
                    Mesh(
                        vertices=[
                            0, r * 1.3, 0, 0,          # Tip
                            -r * 0.9, -r * 0.8, 0, 0,  # Left wing
                            r * 0.9, -r * 0.8, 0, 0    # Right wing
                        ],
                        indices=[0, 1, 2],
                        mode='triangles'
                    )
                    # Cockpit canopy glow
                    Color(1.0, 1.0, 1.0, 0.9)
                    Ellipse(pos=(-r * 0.25, -r * 0.1), size=(r * 0.5, r * 0.7))
                    PopMatrix()

                # Shield Bubble Glow
                if self.player.shield > 0:
                    s_ratio = self.player.shield / self.player.max_shield
                    Color(0.2, 0.8, 1.0, 0.35 + 0.3 * s_ratio)
                    s_rad = self.player.radius * 1.45
                    Line(circle=(self.player.x, self.player.y, s_rad), width=2.0)

            # 9. Heads-Up Display (HUD) Overlays
            if self.player:
                # Hull Health Bar (Bottom Left)
                hp_ratio = max(0.0, min(1.0, self.player.health / self.player.max_health))
                Color(0.1, 0.1, 0.1, 0.8)
                Rectangle(pos=(dp(15), dp(15)), size=(dp(110), dp(10)))
                Color(0.2, 0.9, 0.3, 0.9)
                Rectangle(pos=(dp(15), dp(15)), size=(dp(110) * hp_ratio, dp(10)))

                # Shield Bar (Just above Hull Bar)
                sh_ratio = max(0.0, min(1.0, self.player.shield / self.player.max_shield))
                Color(0.1, 0.1, 0.1, 0.8)
                Rectangle(pos=(dp(15), dp(28)), size=(dp(110), dp(6)))
                Color(0.2, 0.8, 1.0, 0.9)
                Rectangle(pos=(dp(15), dp(28)), size=(dp(110) * sh_ratio, dp(6)))

                # EMP Bomb Button (Bottom Right)
                bomb_x = self.width - dp(45)
                bomb_y = dp(45)
                bomb_color = (0.2, 0.7, 1.0, 0.9) if self.player.bombs_count > 0 else (0.4, 0.4, 0.4, 0.5)
                Color(*bomb_color)
                Ellipse(pos=(bomb_x - dp(24), bomb_y - dp(24)), size=(dp(48), dp(48)))
                Color(1.0, 1.0, 1.0, 0.9)
                Line(circle=(bomb_x, bomb_y, dp(24)), width=1.5)

            PopMatrix()

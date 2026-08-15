"""Particle and visual effects system for Cosmic Defender.
Includes parallax starfields, particle emitters for explosions and thrusters,
floating combat numbers, and screen shake.
"""

import math
import random


class Star:
    """Individual parallax background star."""
    def __init__(self, x, y, layer):
        self.x = x
        self.y = y
        self.layer = layer  # 1 = distant (slow/dim), 2 = mid, 3 = near (fast/bright)
        self.size = 1.0 + layer * 0.8
        self.speed = 40.0 * layer
        self.brightness = 0.3 + (layer * 0.25)
        self.twinkle_speed = random.uniform(2.0, 5.0)
        self.twinkle_phase = random.uniform(0.0, 6.28)


class ParallaxStarfield:
    """Manages 3 layers of scrolling stars for deep space immersion."""
    def __init__(self, width=800, height=600, star_count=70):
        self.width = width
        self.height = height
        self.stars = []
        for _ in range(star_count):
            layer = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
            s = Star(
                random.uniform(0, max(100, width)),
                random.uniform(0, max(100, height)),
                layer
            )
            self.stars.append(s)

    def resize(self, width, height):
        self.width = max(100, width)
        self.height = max(100, height)
        for s in self.stars:
            if s.x > self.width:
                s.x = random.uniform(0, self.width)
            if s.y > self.height:
                s.y = random.uniform(0, self.height)

    def update(self, dt):
        for s in self.stars:
            s.y -= s.speed * dt
            s.twinkle_phase += s.twinkle_speed * dt
            if s.y < 0:
                s.y = self.height + random.uniform(0, 20)
                s.x = random.uniform(0, self.width)


class Particle:
    """Individual dynamic particle."""
    def __init__(self, x, y, vx, vy, color, size, life, shape="circle", decay=1.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.r, self.g, self.b, self.base_a = color
        self.a = self.base_a
        self.size = size
        self.max_life = max(0.01, life)
        self.life = self.max_life
        self.shape = shape
        self.decay = decay

    def update(self, dt):
        self.life -= dt
        if self.life <= 0:
            return False
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Drag / deceleration
        self.vx *= (1.0 - (0.5 * dt))
        self.vy *= (1.0 - (0.5 * dt))

        # Alpha & size decay
        ratio = self.life / self.max_life
        self.a = self.base_a * (ratio ** self.decay)
        return True


class FloatingText:
    """Floating combat text for combos and bonus scores."""
    def __init__(self, text, x, y, color=(1.0, 0.9, 0.2, 1.0), size=18, life=0.9):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.font_size = size
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.life -= dt
        self.y += 45 * dt
        return self.life > 0


class Shockwave:
    """Expanding EMP ring shockwave."""
    def __init__(self, x, y, max_radius=300, duration=0.6, color=(0.3, 0.8, 1.0, 0.9)):
        self.x = x
        self.y = y
        self.current_radius = 5
        self.max_radius = max_radius
        self.duration = duration
        self.elapsed = 0.0
        self.color = color

    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            return False
        prog = self.elapsed / self.duration
        self.current_radius = 5 + (self.max_radius - 5) * (1.0 - (1.0 - prog) ** 2)
        return True


class ParticleSystem:
    """Central manager for visual effects."""
    def __init__(self):
        self.particles = []
        self.floating_texts = []
        self.shockwaves = []
        self.shake_duration = 0.0
        self.shake_intensity = 0.0
        self.shake_offset = (0.0, 0.0)

    def trigger_shake(self, intensity=8.0, duration=0.25):
        """Trigger camera screen-shake effect."""
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_duration = max(self.shake_duration, duration)

    def emit_thruster(self, x, y, color=(0.2, 0.7, 1.0, 0.8)):
        """Emit rocket engine exhaust particles."""
        for _ in range(2):
            vx = random.uniform(-15, 15)
            vy = random.uniform(-140, -80)
            size = random.uniform(3, 7)
            life = random.uniform(0.12, 0.25)
            self.particles.append(Particle(x + random.uniform(-4, 4), y, vx, vy, color, size, life))

    def emit_explosion(self, x, y, count=25, color_theme="fire", scale=1.0):
        """Emit radial burst explosion particles."""
        colors = {
            "fire": [
                (1.0, 0.9, 0.2, 1.0),  # Yellow
                (1.0, 0.5, 0.0, 1.0),  # Orange
                (1.0, 0.15, 0.0, 0.9), # Red
                (0.6, 0.6, 0.6, 0.7)  # Smoke
            ],
            "plasma": [
                (0.2, 0.9, 1.0, 1.0),  # Cyan
                (0.5, 0.3, 1.0, 1.0),  # Purple
                (1.0, 1.0, 1.0, 1.0)   # White
            ],
            "asteroid": [
                (0.7, 0.65, 0.6, 1.0), # Rock Grey
                (0.5, 0.45, 0.4, 0.9), # Dark Rock
                (0.9, 0.6, 0.2, 0.8)   # Spark
            ],
            "gold": [
                (1.0, 0.85, 0.1, 1.0),
                (1.0, 1.0, 0.4, 1.0),
                (1.0, 0.6, 0.0, 0.9)
            ]
        }
        palette = colors.get(color_theme, colors["fire"])
        for _ in range(int(count * scale)):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(40, 240) * scale
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            col = random.choice(palette)
            size = random.uniform(3, 8) * scale
            life = random.uniform(0.25, 0.65)
            self.particles.append(Particle(x, y, vx, vy, col, size, life, decay=1.2))

    def emit_emp_shockwave(self, x, y, max_radius=350):
        self.shockwaves.append(Shockwave(x, y, max_radius=max_radius))
        self.emit_explosion(x, y, count=40, color_theme="plasma", scale=1.5)
        self.trigger_shake(intensity=14.0, duration=0.4)

    def add_floating_text(self, text, x, y, color=(1.0, 0.9, 0.2, 1.0), size=18):
        self.floating_texts.append(FloatingText(text, x, y, color=color, size=size))

    def update(self, dt):
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
        # Update floating combat texts
        self.floating_texts = [ft for ft in self.floating_texts if ft.update(dt)]
        # Update shockwaves
        self.shockwaves = [sw for sw in self.shockwaves if sw.update(dt)]

        # Update screen shake
        if self.shake_duration > 0:
            self.shake_duration -= dt
            ox = random.uniform(-self.shake_intensity, self.shake_intensity)
            oy = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_offset = (ox, oy)
            if self.shake_duration <= 0:
                self.shake_offset = (0.0, 0.0)
                self.shake_intensity = 0.0
        else:
            self.shake_offset = (0.0, 0.0)

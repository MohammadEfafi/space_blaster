"""
entities/enemies/boss_base.py
=============================

کلاس پایه‌ی همه‌ی باس‌ها.

شامل منطق مشترک:
    • ورود به صفحه و sway
    • attack timing loop
    • radial/aimed (حملات پایه که همه می‌تونن استفاده کنن)
    • reset_attack
    • on_death + چک باس‌های دیگه
    • HP bar و fade helpers
    • _darker / _lighter helpers

هر باس باید override کنه:
    • _pick_and_execute_attack  → حملات اختصاصی
    • draw_body                 → ظاهر اختصاصی
"""

from __future__ import annotations

import math
import random
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


class BossBase(Enemy):
    """کلاس پایه‌ی باس‌ها."""

    KIND = EnemyKind.BOSS

    # ---- تنظیمات پیش‌فرض (هر باس override می‌کنه) ----
    HP = 80
    RADIUS = 80
    SPEED = 0.0
    SCORE = 500
    DROP_CHANCE = 1.0
    BODY_COLOR = (180, 60, 220)
    boss_name = "BOSS"

    ENTRY_Y = 180
    SWAY_AMPLITUDE = 140
    SWAY_SPEED = 0.6

    PHASE_2_THRESHOLD = 0.50
    PHASE_3_THRESHOLD = 0.25

    ATTACK_INTERVAL_P1 = 2.2
    ATTACK_INTERVAL_P2 = 1.7
    ATTACK_INTERVAL_P3 = 1.2

    # ─────────────────────────────────────────────────────────────────────

    def __init__(self, x, y, scene=None, *, target_y=None):
        super().__init__(x, y, scene=scene, target_y=target_y)

        self._phase = 1
        self._attack_timer = 1.5
        self._current_attack: str | None = None
        self._attack_progress = 0.0
        self._charge_pos: tuple[float, float] | None = None
        self._charge_particles_timer = 0.0
        self._summon_targets: list[tuple[float, float]] = []

        self._rotation = 0.0
        self._outer_rotation = 0.0
        self._sway_phase = 0.0
        self._danger_flash = 0.0

        self._locked_y = False
        self.sway_amplitude = self.SWAY_AMPLITUDE
        self.sway_phase_offset = 0.0

    # ─────────────────────────────────────────────────────────────────────
    #  حرکت
    # ─────────────────────────────────────────────────────────────────────

    def update_ai(self, dt: float) -> None:
        # ورود
        if not self._locked_y:
            if self.y < self.ENTRY_Y:
                self.y += 60 * dt
            else:
                self.y = self.ENTRY_Y
                self._locked_y = True
                self._base_x = self.x

        # sway
        if self._locked_y:
            self._sway_phase += dt * self.SWAY_SPEED
            self.x = self._base_x + math.sin(
                self._sway_phase + self.sway_phase_offset
            ) * self.sway_amplitude

        # rotation
        self._rotation += dt * (0.6 + self._phase * 0.4)
        self._outer_rotation -= dt * (0.4 + self._phase * 0.2)

        # danger flash
        if self._danger_flash > 0:
            self._danger_flash = max(0.0, self._danger_flash - dt * 3.0)

        # phase
        hp_ratio = self.hp / self.max_hp
        if hp_ratio <= self.PHASE_3_THRESHOLD:
            self._phase = 3
        elif hp_ratio <= self.PHASE_2_THRESHOLD:
            self._phase = 2
        else:
            self._phase = 1

        # attacks
        if self._locked_y:
            self._update_attacks(dt)

    # ─────────────────────────────────────────────────────────────────────
    #  حملات — قابل Override
    # ─────────────────────────────────────────────────────────────────────

    def _update_attacks(self, dt: float) -> None:
        """تایمر ساده. باس‌هایی که state خاص دارن override می‌کنن."""
        self._attack_timer -= dt
        if self._attack_timer <= 0:
            self._pick_and_execute_attack()

    def _pick_and_execute_attack(self) -> None:
        """زیرکلاس‌ها باید پیاده‌سازی کنن."""
        raise NotImplementedError("Each boss must implement _pick_and_execute_attack")

    def _get_attack_interval(self) -> float:
        base = self.ATTACK_INTERVAL_P3 if self._phase == 3 else (
            self.ATTACK_INTERVAL_P2 if self._phase == 2 else self.ATTACK_INTERVAL_P1
        )
        return base * random.uniform(0.9, 1.15)

    def _reset_attack(self) -> None:
        self._current_attack = None
        self._attack_progress = 0.0
        self._charge_pos = None
        self._danger_flash = 0.0
        self._attack_timer = self._get_attack_interval()

    # ---- حملات پایه (همه می‌تونن استفاده کنن) ----

    def _fire_radial(self, n: int = 16, speed: float = 220) -> None:
        if self.scene is None:
            return
        for i in range(n):
            angle = (i / n) * math.tau + self._rotation
            b = Bullet(
                self.x, self.y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
            )
            try:
                self.scene.spawn_bullet(b)
            except Exception:
                pass
        try:
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(4.0)
        except Exception:
            pass

    def _fire_aimed(self, spread_count: int = 5, speed: float = 280) -> None:
        if self.scene is None:
            return
        player = getattr(self.scene, "player", None)
        if player is None:
            return
        dx = player.x - self.x
        dy = player.y - self.y
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d
        for i in range(spread_count):
            spread = (i - (spread_count - 1) / 2) * 0.09
            ca, sa = math.cos(spread), math.sin(spread)
            nx = ux * ca - uy * sa
            ny = ux * sa + uy * ca
            b = Bullet(
                self.x, self.y, nx * speed, ny * speed,
                friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
            )
            try:
                self.scene.spawn_bullet(b)
            except Exception:
                pass
        try:
            self.scene.audio.play("enemy_shoot")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  مرگ
    # ─────────────────────────────────────────────────────────────────────

    def on_death(self) -> None:
        if self.scene is None:
            return
        try:
            self.scene.particles.preset_boss_explosion(self.x, self.y)
            self.scene.add_score(self.score_value)
            self.scene.audio.play("player_explode")
            self.scene.camera.shake(28.0, aftershock=4)
            self.scene.spawn_powerup(self.x, self.y)
            self.scene.spawn_powerup(self.x - 40, self.y)
            self.scene.spawn_powerup(self.x + 40, self.y)

            # اگه هنوز باس دیگه‌ای زنده‌ست، پیام پیروزی نده
            others_alive = False
            try:
                for e in self.scene.enemies:
                    if e is not self and e.alive and isinstance(e, BossBase):
                        others_alive = True
                        break
            except Exception:
                pass

            if not others_alive and hasattr(self.scene, "on_boss_defeated"):
                self.scene.on_boss_defeated()
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  draw_body — قابل Override
    # ─────────────────────────────────────────────────────────────────────

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        raise NotImplementedError("Each boss must implement draw_body")

    # ─────────────────────────────────────────────────────────────────────
    #  Helpers مشترک
    # ─────────────────────────────────────────────────────────────────────

    def _draw_hp_bar(self, surface, cx, cy, r):
        w = int(r * 2)
        h = 6
        x = cx - w // 2
        y = cy + int(r * 1.25)
        bg = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 200))
        surface.blit(bg, (x - 2, y - 2))
        ratio = max(0.0, self.hp / self.max_hp)
        color = (255, 60, 60) if ratio > 0.5 else (255, 150, 40) if ratio > 0.25 else (255, 80, 255)
        pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
        pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 2)

    def _apply_fade(self, surface, cx, cy, r, alpha):
        a = 255 - alpha
        if a <= 0:
            return
        fade = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(a * 0.7)))
        surface.blit(fade, (cx - r * 2, cy - r * 2))

    @staticmethod
    def _darker(c, amount):
        return (max(0, c[0] - amount), max(0, c[1] - amount), max(0, c[2] - amount))

    @staticmethod
    def _lighter(c, amount):
        return (min(255, c[0] + amount), min(255, c[1] + amount), min(255, c[2] + amount))


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers رسم با آلفا
# ═══════════════════════════════════════════════════════════════════════════

def draw_poly_alpha(surface, points, color, width=0):
    if not points:
        return
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = int(min(xs)) - 2, int(max(xs)) + 2
    min_y, max_y = int(min(ys)) - 2, int(max(ys)) + 2
    w = max_x - min_x
    h = max_y - min_y
    if w <= 0 or h <= 0:
        return
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    local = [(p[0] - min_x, p[1] - min_y) for p in points]
    if width > 0:
        pygame.draw.polygon(tmp, color, local, width)
    else:
        pygame.draw.polygon(tmp, color, local)
    surface.blit(tmp, (min_x, min_y))


def draw_line_alpha(surface, color, p1, p2, width=1):
    x1, y1 = int(p1[0]), int(p1[1])
    x2, y2 = int(p2[0]), int(p2[1])
    ox = min(x1, x2) - 4
    oy = min(y1, y2) - 4
    w = abs(x2 - x1) + 8
    h = abs(y2 - y1) + 8
    if w <= 0 or h <= 0:
        return
    tmp = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.line(tmp, color, (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), width)
    surface.blit(tmp, (ox, oy))


__all__ = ["BossBase", "draw_poly_alpha", "draw_line_alpha"]
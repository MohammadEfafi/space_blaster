"""
SENTINEL — تک‌تیرانداز سنگین (نسخه‌ی نهایی).

ظاهر: برج تک‌تیرانداز sci-fi با ۴ پای تلسکوپی، چشم شیطانی که بازیکن
رو دنبال می‌کنه، لوله‌ی اسلحه‌ی بلند، و اتصالات انرژی درخشان.
"""

from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


class SentinelEnemy(Enemy):
    """SENTINEL — تک‌تیرانداز."""

    KIND = EnemyKind.SENTINEL

    HP = 5
    RADIUS = 22
    SPEED = 60
    SCORE = 60
    DROP_CHANCE = 0.30
    SHOOT_CD = 3.0
    BULLET_SPEED = 500
    BODY_COLOR = (220, 60, 80)

    STOP_Y = 220
    AIM_TIME = 1.5

    def _configure(self) -> None:
        self._stopped = False
        self._aim_timer = 0.0
        self._aiming = False
        self._aim_target = (0.0, 0.0)
        self._eye_look = (0.0, 0.0)
        self._pulse = 0.0
        self._leg_phases = [0.0, 0.0, 0.0, 0.0]

    def update_ai(self, dt: float) -> None:
        self._pulse += dt
        for i in range(4):
            self._leg_phases[i] += dt

        if not self._stopped:
            self.y += self.SPEED * dt
            if self.y >= self.STOP_Y:
                self.y = self.STOP_Y
                self._stopped = True
            return

        # ---- چشم بازیکن رو دنبال می‌کنه ----
        player = getattr(self.scene, "player", None) if self.scene else None
        if player and player.alive:
            dx = player.x - self.x
            dy = player.y - self.y
            d = math.hypot(dx, dy) or 1.0
            target = (dx / d, dy / d)
            blend = min(1.0, dt * 5.0)
            self._eye_look = (
                self._eye_look[0] + (target[0] - self._eye_look[0]) * blend,
                self._eye_look[1] + (target[1] - self._eye_look[1]) * blend,
            )

        # ---- نشانه‌گیری ----
        if self._aiming:
            self._aim_timer -= dt
            if player and player.alive:
                self._aim_target = (player.x, player.y)
            if self._aim_timer <= 0:
                self._fire_aimed_shot()
                self._aiming = False

    def _do_shoot(self) -> list:
        if not self._stopped or self._aiming:
            return []
        player = getattr(self.scene, "player", None) if self.scene else None
        if player and player.alive:
            self._aim_target = (player.x, player.y)
        self._aiming = True
        self._aim_timer = self.AIM_TIME
        return []

    def _fire_aimed_shot(self) -> None:
        if self.scene is None:
            return
        dx = self._aim_target[0] - self.x
        dy = self._aim_target[1] - self.y
        d = math.hypot(dx, dy) or 1.0
        vx = (dx / d) * self.BULLET_SPEED
        vy = (dy / d) * self.BULLET_SPEED
        try:
            b = Bullet(
                self.x, self.y + self.radius,
                vx, vy,
                friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
            )
            b.radius = 10
            b.damage = 2
            self.scene.spawn_bullet(b)
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(5.0)
        except Exception:
            pass

    # ═════════════════════════════════════════════════════════════════════
    #  رسم — برج تک‌تیرانداز
    # ═════════════════════════════════════════════════════════════════════

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = int(self.radius * 1.2)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 110)
        darker = self._darker(base, 170)
        bright = self._lighter(base, 80)
        eye_color = (255, 240, 100) if self._aiming else (255, 80, 80)

        # ---- ۱. Laser Sight ----
        if self._aiming:
            tx, ty = self._aim_target
            progress = 1.0 - (self._aim_timer / self.AIM_TIME)
            pulse = 0.5 + 0.5 * math.sin(self._aim_timer * 25)

            # خط laser
            line_alpha = int(200 * (0.3 + progress * 0.7) * pulse)
            line_width = 1 + int(progress * 3)
            dx = tx - cx
            dy = ty - cy
            d = math.hypot(dx, dy) or 1.0
            ex = cx + (dx / d) * 2000
            ey = cy + (dy / d) * 2000
            tmp = pygame.Surface((abs(int(ex - cx)) + 20, abs(int(ey - cy)) + 20), pygame.SRCALPHA)
            ox = min(cx, ex) - 10
            oy = min(cy, ey) - 10
            pygame.draw.line(
                tmp, (255, 60, 60, line_alpha),
                (cx - ox, cy - oy), (ex - ox, ey - oy), line_width,
            )
            surface.blit(tmp, (ox, oy))

            # دایره‌ی هدف
            target_r = int(18 + 12 * pulse)
            for rr in range(target_r, 0, -2):
                a = int(200 * (1 - rr / target_r) * pulse)
                if a > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (255, 60, 60, a), (rr * 2, rr * 2), rr, 3)
                    surface.blit(g, (int(tx) - rr * 2, int(ty) - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۲. سایه‌ی زیر ----
        sw, sh = int(r * 1.3), int(r * 0.4)
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)
        for rr in range(sh, 0, -1):
            a = int(90 * (1 - rr / sh) ** 1.5)
            if a > 0:
                pygame.draw.ellipse(shadow, (0, 0, 0, a),
                                    (sw - rr, sh - rr, rr * 2, rr * 2))
        surface.blit(shadow, (cx - sw, cy + int(r * 0.55) - sh))

        # ---- ۳. ۴ پای تلسکوپی (زاویه‌ای) ----
        for i in range(4):
            angle = math.pi / 4 + i * math.pi / 2
            wave = math.sin(self._leg_phases[i] * 2) * 3

            base_x = cx + math.cos(angle) * r * 0.5
            base_y = cy + int(r * 0.3) + math.sin(angle) * r * 0.15
            knee_x = cx + math.cos(angle) * r * 0.85
            knee_y = cy + int(r * 0.45) + math.sin(angle) * r * 0.25 + wave
            tip_x = cx + math.cos(angle) * r * 1.15
            tip_y = cy + int(r * 0.6) + math.sin(angle) * r * 0.35 + wave

            # پای تیره
            pygame.draw.line(surface, darker,
                             (int(base_x), int(base_y)),
                             (int(knee_x), int(knee_y)), 6)
            pygame.draw.line(surface, dark,
                             (int(knee_x), int(knee_y)),
                             (int(tip_x), int(tip_y)), 5)
            # خط روشن
            pygame.draw.line(surface, bright,
                             (int(knee_x), int(knee_y)),
                             (int(tip_x), int(tip_y)), 1)

            # مفصل زانو
            pygame.draw.circle(surface, bright, (int(knee_x), int(knee_y)), 3)
            # نوک پا
            pygame.draw.circle(surface, base, (int(tip_x), int(tip_y)), 4)
            pygame.draw.circle(surface, bright, (int(tip_x), int(tip_y)), 4, 1)

        # ---- ۴. بدنه‌ی برج (سه‌لایه) ----
        # لایه‌ی بیرونی (سایه)
        tower_outer = [
            (cx - int(r * 0.6), cy + int(r * 0.4)),
            (cx - int(r * 0.55), cy - int(r * 0.6)),
            (cx - int(r * 0.4), cy - int(r * 1.0)),
            (cx + int(r * 0.4), cy - int(r * 1.0)),
            (cx + int(r * 0.55), cy - int(r * 0.6)),
            (cx + int(r * 0.6), cy + int(r * 0.4)),
        ]
        pygame.draw.polygon(surface, darker, [(x, y + 3) for x, y in tower_outer])

        # لایه‌ی میانی
        tower_mid = [
            (cx - int(r * 0.5), cy + int(r * 0.35)),
            (cx - int(r * 0.45), cy - int(r * 0.55)),
            (cx - int(r * 0.32), cy - int(r * 0.9)),
            (cx + int(r * 0.32), cy - int(r * 0.9)),
            (cx + int(r * 0.45), cy - int(r * 0.55)),
            (cx + int(r * 0.5), cy + int(r * 0.35)),
        ]
        pygame.draw.polygon(surface, base, tower_mid)

        # خطوط زره‌ای
        for i in range(3):
            y_line = cy - int(r * 0.5) + i * int(r * 0.3)
            pygame.draw.line(surface, darker,
                             (cx - int(r * 0.45), y_line),
                             (cx + int(r * 0.45), y_line), 2)

        # خطوط کناری (لبه‌ی نئونی)
        pygame.draw.polygon(surface, bright, tower_mid, 2)

        # ---- ۵. کابین و چشم شیطانی ----
        cab_y = cy - int(r * 0.65)
        cab_r = max(6, int(r * 0.32))

        # هاله‌ی چشم
        glow_r = cab_r * 4
        glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for rr in range(glow_r, 0, -2):
            a = int(180 * (1 - rr / glow_r))
            if a > 0:
                pygame.draw.circle(glow, (*eye_color, a), (glow_r, glow_r), rr)
        surface.blit(glow, (cx - glow_r, cab_y - glow_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # قاب کابین
        pygame.draw.circle(surface, darker, (cx, cab_y), cab_r + 2)
        pygame.draw.circle(surface, base, (cx, cab_y), cab_r)
        pygame.draw.circle(surface, bright, (cx, cab_y), cab_r, 2)

        # چشم (با نگاه)
        eye_x = cx + int(self._eye_look[0] * cab_r * 0.3)
        eye_y = cab_y + int(self._eye_look[1] * cab_r * 0.3)
        pygame.draw.circle(surface, eye_color, (eye_x, eye_y), max(3, cab_r - 3))
        pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y), max(1, cab_r // 2))

        # ---- ۶. لوله‌ی اسلحه (بلند، پایین) ----
        barrel_y = cy + int(r * 0.3)
        barrel_w = int(r * 0.15)
        barrel_h = int(r * 0.55)
        pygame.draw.rect(surface, darker,
                         (cx - barrel_w, barrel_y, barrel_w * 2, barrel_h))
        pygame.draw.rect(surface, base,
                         (cx - barrel_w + 1, barrel_y, barrel_w * 2 - 2, barrel_h))
        pygame.draw.rect(surface, bright,
                         (cx - barrel_w, barrel_y, barrel_w * 2, barrel_h), 2)

        # خطوط زره روی لوله
        for i in range(2):
            ly = barrel_y + int(barrel_h * (0.3 + i * 0.4))
            pygame.draw.line(surface, bright,
                             (cx - barrel_w, ly), (cx + barrel_w, ly), 1)

        # دهانه‌ی درخشان
        tip_y = barrel_y + barrel_h
        for rr in range(10, 0, -2):
            a = int(180 * (1 - rr / 10))
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*eye_color, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, tip_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.circle(surface, (30, 30, 40), (cx, tip_y), 5)
        pygame.draw.circle(surface, eye_color, (cx, tip_y), 3)

        # ---- ۷. اتصالات انرژی (خطوط درخشان روی برج) ----
        if self._stopped:
            pulse = 0.5 + 0.5 * math.sin(self._pulse * 4)
            a = int(180 * pulse)
            if a > 0:
                for sign in (-1, 1):
                    x1 = cx + sign * int(r * 0.35)
                    y1 = cy - int(r * 0.5)
                    x2 = cx + sign * int(r * 0.25)
                    y2 = cy + int(r * 0.3)
                    line = pygame.Surface((abs(x2 - x1) + 10, abs(y2 - y1) + 10), pygame.SRCALPHA)
                    ox, oy = min(x1, x2) - 5, min(y1, y2) - 5
                    pygame.draw.line(line, (255, 100, 60, a),
                                     (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), 2)
                    surface.blit(line, (ox, oy))

        # ---- ۸. نشانگر شارژ ----
        if self._aiming:
            progress = 1.0 - (self._aim_timer / self.AIM_TIME)
            bar_w = int(r * 1.4)
            bar_h = 5
            bar_x = cx - bar_w // 2
            bar_y = cy - int(r * 1.3)
            pygame.draw.rect(surface, (20, 20, 30),
                             (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4))
            pygame.draw.rect(surface, (40, 40, 50),
                             (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(surface, eye_color,
                             (bar_x, bar_y, int(bar_w * progress), bar_h))
            pygame.draw.rect(surface, (255, 255, 255),
                             (bar_x, bar_y, bar_w, bar_h), 1)

        # ---- ۹. نوار HP ----
        if self.hp < self.max_hp:
            w = int(r * 1.8)
            h = 5
            x = cx - w // 2
            y = cy + int(r * 0.8)
            bg = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 220))
            surface.blit(bg, (x - 2, y - 2))
            ratio = max(0.0, self.hp / self.max_hp)
            color = (80, 255, 140) if ratio > 0.5 else (255, 220, 60) if ratio > 0.25 else (255, 60, 60)
            pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
            pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 1)

    @staticmethod
    def _darker(c, amount):
        return (max(0, c[0] - amount), max(0, c[1] - amount), max(0, c[2] - amount))

    @staticmethod
    def _lighter(c, amount):
        return (min(255, c[0] + amount), min(255, c[1] + amount), min(255, c[2] + amount))


__all__ = ["SentinelEnemy"]
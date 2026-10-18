"""
SPECTER — شبح فازنده (نسخه‌ی بازطراحی‌شده).
"""
from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.enemies.base import Enemy, EnemyKind


class SpecterEnemy(Enemy):
    """SPECTER — شبح فازنده."""

    KIND = EnemyKind.SPECTER

    HP = 2
    RADIUS = 18
    SPEED = 95
    SCORE = 40
    DROP_CHANCE = 0.20
    SHOOT_CD = 2.0
    BULLET_SPEED = 220
    BODY_COLOR = (200, 110, 255)

    VISIBLE_DURATION = 1.4
    INVISIBLE_DURATION = 0.9

    def _configure(self) -> None:
        self._phase_timer = 0.0
        self._visible = True
        self._alpha = 1.0
        # ذرات orbit
        self._orbits = [random.uniform(0, math.tau) for _ in range(4)] if False else [i * math.tau / 4 for i in range(4)]

    def update_ai(self, dt: float) -> None:
        self.y += self.SPEED * dt
        self._phase_timer += dt

        if self._visible:
            if self._phase_timer >= self.VISIBLE_DURATION:
                self._phase_timer = 0.0
                self._visible = False
            self._alpha = min(1.0, self._alpha + dt * 4.0)
        else:
            if self._phase_timer >= self.INVISIBLE_DURATION:
                self._phase_timer = 0.0
                self._visible = True
            self._alpha = max(0.05, self._alpha - dt * 4.0)

    def take_damage(self, damage: int) -> bool:
        if not self._visible:
            return False
        return super().take_damage(damage)

    def _do_shoot(self) -> list:
        if not self._visible:
            return []
        return super()._do_shoot()

    # ═════════════════════════════════════════════════════════════════════
    #  رسم — WRAITH (نسخه‌ی افسانه‌ای)
    # ═════════════════════════════════════════════════════════════════════

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = int(self.radius * 1.3)
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 110)
        bright = self._lighter(base, 90)
        white = (255, 240, 255)

        a = int(self._alpha * alpha)
        if a <= 8:
            # فقط هاله‌ی خیلی کم برای این‌که کاربر بدونه کجاست
            ghost = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
            for rr in range(r * 2, 0, -3):
                alpha_val = int(30 * (1 - rr / (r * 2)))
                if alpha_val > 0:
                    pygame.draw.circle(ghost, (*base, alpha_val), (r * 2, r * 2), rr)
            surface.blit(ghost, (cx - r * 2, cy - r * 2),
                         special_flags=pygame.BLEND_RGBA_ADD)
            return

        alpha_frac = a / 255.0

        # ---- ۱. هاله‌ی سه‌لایه ----
        aura_r = int(r * 2.2)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -4):
            aa = int(70 * (1 - rr / aura_r) ** 2 * alpha_frac)
            if aa > 0:
                pygame.draw.circle(aura, (*base, aa), (aura_r, aura_r), rr)
        # لایه‌ی سفید-نزدیک مرکز
        for rr in range(int(aura_r * 0.5), 0, -2):
            aa = int(60 * (1 - rr / (aura_r * 0.5)) * alpha_frac)
            if aa > 0:
                pygame.draw.circle(aura, (255, 240, 255, aa), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۲. دُم‌های موج‌دار (۵ تا، بلند، زیگزاگ) ----
        for i in range(5):
            t = (i - 2) / 2.0
            phase = self._t * 4 + i * 1.1
            wave_x = math.sin(phase) * 14
            tx = cx + int(t * r * 0.7) + int(wave_x)
            ty = cy + int(r * 0.35)
            tail_len = int(r * (1.0 + abs(t) * 0.4))

            # نقاط زیگزاگ
            pts = [(tx, ty)]
            segs = 4
            for j in range(1, segs + 1):
                tj = j / segs
                px = tx + int(math.sin(phase + j * 1.3) * r * 0.15 * tj)
                py = ty + int(tail_len * tj)
                pts.append((px, py))

            # هاله‌ی دُم
            for rr in range(int(r * 0.25), 0, -2):
                aa = int(100 * (1 - rr / (r * 0.25)) * alpha_frac)
                if aa > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (*bright, aa), (rr * 2, rr * 2), rr)
                    surface.blit(g, (tx - rr * 2, ty + tail_len // 2 - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

            # خط زیگزاگ
            for j in range(len(pts) - 1):
                w = max(1, int(4 * (1 - j / len(pts))))
                aa = int(200 * (1 - j / len(pts)) * alpha_frac)
                if aa > 0:
                    x1, y1 = pts[j]
                    x2, y2 = pts[j + 1]
                    tmp = pygame.Surface((abs(x2 - x1) + 8, abs(y2 - y1) + 8), pygame.SRCALPHA)
                    ox, oy = min(x1, x2) - 4, min(y1, y2) - 4
                    pygame.draw.line(tmp, (*bright, aa), (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), w)
                    surface.blit(tmp, (ox, oy))

        # ---- ۳. ذرات orbit (۴ ذره‌ی کوچیک) ----
        orbit_r = r * 1.1
        for i in range(4):
            angle = self._orbits[i] + self._t * 1.5
            px = cx + int(math.cos(angle) * orbit_r)
            py = cy + int(math.sin(angle) * orbit_r * 0.7)
            size = 2
            g = pygame.Surface((size * 8, size * 8), pygame.SRCALPHA)
            for rr in range(size * 4, 0, -1):
                aa = int(180 * (1 - rr / (size * 4)) * alpha_frac)
                if aa > 0:
                    pygame.draw.circle(g, (*white, aa), (size * 4, size * 4), rr)
            surface.blit(g, (px - size * 4, py - size * 4),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۴. بدنه‌ی شبح‌وار (سه‌لایه) ----
        rot = self._t * 1.2

        # لایه‌ی بیرونی (چادر)
        outer_pts = []
        for i in range(16):
            angle = rot + i * math.tau / 16
            wobble = 1.0 + 0.18 * math.sin(self._t * 3.5 + i * 0.8)
            outer_pts.append((
                cx + math.cos(angle) * r * wobble,
                cy + math.sin(angle) * r * 0.95 * wobble,
            ))
        tmp = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
        local = [(p[0] - cx + r * 2.5, p[1] - cy + r * 2.5) for p in outer_pts]
        pygame.draw.polygon(tmp, (*base, int(160 * alpha_frac)), local)
        pygame.draw.polygon(tmp, (*bright, int(255 * alpha_frac)), local, 2)
        surface.blit(tmp, (cx - r * 2.5, cy - r * 2.5))

        # لایه‌ی میانی
        mid_pts = []
        for i in range(12):
            angle = -rot * 0.7 + i * math.tau / 12
            wobble = 1.0 + 0.1 * math.sin(self._t * 4 + i * 1.5)
            mid_pts.append((
                cx + math.cos(angle) * r * 0.65 * wobble,
                cy + math.sin(angle) * r * 0.6 * wobble,
            ))
        tmp2 = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
        local2 = [(p[0] - cx + r * 2.5, p[1] - cy + r * 2.5) for p in mid_pts]
        pygame.draw.polygon(tmp2, (*dark, int(200 * alpha_frac)), local2)
        surface.blit(tmp2, (cx - r * 2.5, cy - r * 2.5))

        # ---- ۵. هسته‌ی درخشان ----
        pulse = 0.7 + 0.3 * math.sin(self._t * 6)
        core_r = int(r * 0.35 * pulse)

        for rr in range(int(r * 0.6), 0, -3):
            aa = int(200 * (1 - rr / (r * 0.6)) ** 1.5 * pulse * alpha_frac)
            if aa > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 240, 255, aa), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, cy - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # هسته (سه لایه)
        pygame.draw.circle(surface, base, (cx, cy), max(1, int(core_r * alpha_frac)))
        pygame.draw.circle(surface, bright, (cx, cy), max(1, int(core_r * 0.7 * alpha_frac)))
        pygame.draw.circle(surface, white, (cx, cy), max(1, int(core_r * 0.4 * alpha_frac)))

        # ---- ۶. سه چشم شیطانی ----
        eye_positions = [
            (cx - int(r * 0.35), cy - int(r * 0.15)),
            (cx + int(r * 0.35), cy - int(r * 0.15)),
            (cx, cy - int(r * 0.45)),
        ]
        for idx, (ex, ey) in enumerate(eye_positions):
            eye_r = max(3, int(r * 0.10))
            # هاله
            for rr in range(eye_r * 4, 0, -1):
                aa = int(180 * (1 - rr / (eye_r * 4)) * alpha_frac)
                if aa > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (*white, aa), (rr * 2, rr * 2), rr)
                    surface.blit(g, (ex - rr * 2, ey - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)
            # سفیدی چشم
            pygame.draw.circle(surface, (255, 255, 255, a), (ex, ey), eye_r)
            # مردمک (صورتی)
            pygame.draw.circle(surface, (*base, a), (ex, ey), max(1, eye_r // 2))
            # برق
            pygame.draw.circle(surface, (255, 255, 255, a),
                               (ex - 1, ey - 1), max(1, eye_r // 4))

        # ---- ۷. هشدار ناپدید شدن ----
        if self._visible and self._phase_timer > self.VISIBLE_DURATION * 0.65:
            progress = (self._phase_timer - self.VISIBLE_DURATION * 0.65) / (self.VISIBLE_DURATION * 0.35)
            warn_r = int(r * (1.2 + progress * 0.8))
            # دایره‌ی نازک
            for i in range(int(warn_r * 0.5)):
                angle = (i / (warn_r * 0.5)) * math.tau + self._t * 3
                wx = cx + int(math.cos(angle) * warn_r)
                wy = cy + int(math.sin(angle) * warn_r)
                aa = int(200 * progress * (1 - abs(i / (warn_r * 0.5) - 0.5) * 2) * alpha_frac)
                if aa > 0:
                    pygame.draw.circle(surface, (255, 200, 100, aa), (wx, wy), 2)

        # ---- ۸. نوار HP ----
        if self.hp < self.max_hp:
            w = int(r * 2)
            h = 3
            x = cx - w // 2
            y = cy - int(r * 1.4)
            bg = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            surface.blit(bg, (x - 1, y - 1))
            ratio = max(0.0, self.hp / self.max_hp)
            pygame.draw.rect(surface, (255, 80, 255), (x, y, int(w * ratio), h))

    @staticmethod
    def _darker(c, amount):
        return (max(0, c[0] - amount), max(0, c[1] - amount), max(0, c[2] - amount))

    @staticmethod
    def _lighter(c, amount):
        return (min(255, c[0] + amount), min(255, c[1] + amount), min(255, c[2] + amount))


__all__ = ["SpecterEnemy"]
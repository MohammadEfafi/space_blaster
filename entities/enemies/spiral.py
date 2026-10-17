"""
entities/enemies/spiral.py
==========================

دشمن نوع سوم — WRAITH (شبح).

طراحی تهاجمی:
    • بدنه‌ی شبح‌مانند (بالا پهن، پایین باریک)
    • دُم‌های اتری موج‌دار (تکان‌دار)
    • دو چشم قرمز شیطانی
    • هاله‌ی بنفش/سبز مرموز
    • حرکت سینوسی + چرخش

رفتار:
    • حرکت مارپیچ
    • سریع
    • بدون شلیک
"""

from __future__ import annotations

import math
import random
import pygame

from core import settings as S
from entities.enemies.base import Enemy, EnemyKind


class SpiralEnemy(Enemy):
    """WRAITH — شبح مواج."""

    KIND = EnemyKind.SPIRAL

    HP          = S.EnemyCfg.Spiral.HP
    RADIUS      = S.EnemyCfg.Spiral.RADIUS
    SPEED       = S.EnemyCfg.Spiral.SPEED
    SCORE       = S.EnemyCfg.Spiral.SCORE
    DROP_CHANCE = S.EnemyCfg.Spiral.DROP_CHANCE
    AMPLITUDE   = S.EnemyCfg.Spiral.AMPLITUDE
    FREQUENCY   = S.EnemyCfg.Spiral.FREQUENCY
    BODY_COLOR  = S.Palette.ENEMY_SPIRAL

    def _configure(self) -> None:
        self._phase = random.uniform(0, math.tau)

    def update_ai(self, dt: float) -> None:
        self.y += self.SPEED * dt
        self.x = self._base_x + math.sin(self._t * self.FREQUENCY + self._phase) * self.AMPLITUDE
        self.angle = self._t * 180.0

    # ─────────────────────────────────────────────────────────────────────

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = max(10, int(self.radius * 1.25))
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 80)
        darker = self._darker(base, 130)
        bright = self._lighter(base, 70)

        # ---- ۱. دُم‌های موج‌دار (پشت) ----
        self._draw_tails(surface, cx, cy, r, base, dark)

        # ---- ۲. بدنه‌ی شبح ----
        self._draw_body_shape(surface, cx, cy, r, base, dark, bright)

        # ---- ۳. دو چشم شیطانی ----
        self._draw_eyes(surface, cx, cy, r)

        # ---- ۴. خطوط اتریک ----
        self._draw_ethereal_lines(surface, cx, cy, r, darker)

        # ---- ۵. فید ----
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    def _draw_tails(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        base: tuple[int, int, int],
        dark: tuple[int, int, int],
    ) -> None:
        """سه دُم موج‌دار (پشت شبح)."""
        for i, sign in enumerate((-1, 0, 1)):
            # موج سینوسی دُم
            wave = math.sin(self._t * 4.0 + i * 1.5) * r * 0.15

            # نقاط دُم
            tail_x = cx + sign * int(r * 0.4) + int(wave)
            tail_y = cy - int(r * 1.2)
            tail_len = int(r * 1.0) + i * 4

            # هاله‌ی سبز
            for rr in range(8, 0, -2):
                a = int(80 * (1 - rr / 8))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*base, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (tail_x - rr * 2, tail_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

            # خود دُم
            pygame.draw.polygon(surface, dark, [
                (tail_x - int(r * 0.15), tail_y + 4),
                (tail_x + int(r * 0.15), tail_y + 4),
                (tail_x + sign * 8 + int(wave), tail_y - tail_len),
            ])
            pygame.draw.polygon(surface, base, [
                (tail_x - int(r * 0.08), tail_y + 2),
                (tail_x + int(r * 0.08), tail_y + 2),
                (tail_x + sign * 4 + int(wave), tail_y - int(tail_len * 0.7)),
            ])

    def _draw_body_shape(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        base: tuple[int, int, int],
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """بدنه‌ی شبح: بالا پهن، پایین چروکیده."""
        # بدنه با یال‌های پایین (چروکیده)
        hull = [
            (cx,                  cy - int(r * 0.9)),    # بالای سر
            (cx - int(r * 0.7),   cy - int(r * 0.3)),    # شانه چپ
            (cx - int(r * 0.5),   cy + int(r * 0.2)),    # پهلو چپ
            (cx - int(r * 0.65),  cy + int(r * 0.7)),    # یال ۱ چپ
            (cx - int(r * 0.4),   cy + int(r * 0.55)),   # شکاف
            (cx - int(r * 0.2),   cy + int(r * 0.9)),    # یال ۲
            (cx,                  cy + int(r * 0.7)),    # شکاف وسط
            (cx + int(r * 0.2),   cy + int(r * 0.9)),    # یال ۳
            (cx + int(r * 0.4),   cy + int(r * 0.55)),   # شکاف
            (cx + int(r * 0.65),  cy + int(r * 0.7)),    # یال ۴ راست
            (cx + int(r * 0.5),   cy + int(r * 0.2)),    # پهلو راست
            (cx + int(r * 0.7),   cy - int(r * 0.3)),    # شانه راست
        ]

        # سایه
        shadow = [(x, y + 2) for (x, y) in hull]
        pygame.draw.polygon(surface, dark, shadow)

        # بدنه
        pygame.draw.polygon(surface, base, hull)
        pygame.draw.polygon(surface, bright, hull, 2)

        # درخشش داخلی
        inner = [
            (cx,                  cy - int(r * 0.7)),
            (cx - int(r * 0.4),   cy - int(r * 0.2)),
            (cx - int(r * 0.3),   cy + int(r * 0.3)),
            (cx,                  cy + int(r * 0.5)),
            (cx + int(r * 0.3),   cy + int(r * 0.3)),
            (cx + int(r * 0.4),   cy - int(r * 0.2)),
        ]
        pygame.draw.polygon(surface, self._lighter(base, 30), inner)

    def _draw_eyes(self, surface: pygame.Surface, cx: int, cy: int, r: int) -> None:
        """دو چشم قرمز شیطانی."""
        eye_y = cy - int(r * 0.25)
        eye_offset = int(r * 0.28)
        eye_r = max(2, int(r * 0.14))

        for sign in (-1, 1):
            ex = cx + sign * eye_offset

            # هاله
            glow_size = eye_r * 4
            glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            for rr in range(glow_size, 0, -1):
                a = int(150 * (1 - rr / glow_size))
                if a <= 0:
                    continue
                pygame.draw.circle(glow, (255, 40, 40, a),
                                   (glow_size, glow_size), rr)
            surface.blit(glow, (ex - glow_size, eye_y - glow_size),
                         special_flags=pygame.BLEND_RGBA_ADD)

            # خود چشم (بیضی عمودی)
            eye_surf = pygame.Surface((eye_r * 3, eye_r * 4), pygame.SRCALPHA)
            pygame.draw.ellipse(eye_surf, (255, 40, 40),
                                (0, 0, eye_r * 3, eye_r * 4))
            pygame.draw.ellipse(eye_surf, (255, 200, 200),
                                (eye_r, eye_r, eye_r, eye_r * 2))
            surface.blit(eye_surf, (ex - eye_r * 1.5, eye_y - eye_r * 2))

    def _draw_ethereal_lines(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        darker: tuple[int, int, int],
    ) -> None:
        """خطوط موج‌دار روی بدنه."""
        for i in range(3):
            y = cy - int(r * 0.3) + i * int(r * 0.25)
            w = int(r * 0.35) - i * 3
            pygame.draw.line(
                surface, darker,
                (cx - w, y), (cx + w, y), 1,
            )

    def _apply_fade(
        self, surface: pygame.Surface, cx: int, cy: int, r: int, alpha: int,
    ) -> None:
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


__all__ = ["SpiralEnemy"]
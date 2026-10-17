"""
entities/enemies/normal.py
==========================

دشمن نوع اول — STINGER DRONE (زنبور نیش‌زن).

طراحی تهاجمی:
    • بدنه‌ی تیز پیکانی رو به پایین
    • بال‌های مثلثی تیز بیرون‌زده
    • چشم قرمز درخشان با هاله (تهدید)
    • دو موتور کناری با شعله‌ی نارنجی
    • خطوط زره‌ای روی بدنه
    • هیچ شباهتی به پاورآپ یا جمع‌آوری‌کردنی نداره

رفتار:
    • سریع‌ترین دشمن
    • یک ضربه و نابود
    • بدون شلیک
"""

from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.enemies.base import Enemy, EnemyKind


class NormalEnemy(Enemy):
    """STINGER DRONE — رهگیر تیز و تهاجمی."""

    KIND = EnemyKind.NORMAL

    HP          = S.EnemyCfg.Normal.HP
    RADIUS      = S.EnemyCfg.Normal.RADIUS
    SPEED       = S.EnemyCfg.Normal.SPEED
    SCORE       = S.EnemyCfg.Normal.SCORE
    DROP_CHANCE = S.EnemyCfg.Normal.DROP_CHANCE
    BODY_COLOR  = S.Palette.ENEMY_NORMAL

    # ─────────────────────────────────────────────────────────────────────

    def update_ai(self, dt: float) -> None:
        """حرکت مستقیم به پایین."""
        self.y += self.SPEED * dt

    # ─────────────────────────────────────────────────────────────────────
    #  رسم
    # ─────────────────────────────────────────────────────────────────────

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        # بصری بزرگ‌تر از hitbox
        r = max(8, int(self.radius * 1.3))
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        darker = self._darker(base, 150)
        bright = self._lighter(base, 70)

        # ---- ۱. بال‌های تیز بیرونی ----
        self._draw_wings(surface, cx, cy, r, dark, bright)

        # ---- ۲. موتورهای کناری با شعله ----
        self._draw_engines(surface, cx, cy, r)

        # ---- ۳. بدنه‌ی اصلی پیکانی ----
        self._draw_hull(surface, cx, cy, r, base, dark, bright)

        # ---- ۴. خطوط زره ----
        self._draw_armor_lines(surface, cx, cy, r, darker)

        # ---- ۵. چشم قرمز درخشان ----
        self._draw_eye(surface, cx, cy, r)

        # ---- ۶. فید ورود ----
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    # ─────────────────────────────────────────────────────────────────────

    def _draw_wings(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """بال‌های تیز پیکانی (رو به پایین)."""
        # بال چپ
        left = [
            (cx - int(r * 0.25), cy - int(r * 0.6)),    # بالا-داخلی
            (cx - int(r * 1.1),  cy - int(r * 0.15)),   # نوک بالا-چپ
            (cx - int(r * 0.95), cy + int(r * 0.35)),   # نوک پایین-چپ
            (cx - int(r * 0.2),  cy + int(r * 0.1)),    # پایین-داخلی
        ]
        right = [(cx + (cx - x), y) for (x, y) in left]

        pygame.draw.polygon(surface, dark, left)
        pygame.draw.polygon(surface, dark, right)
        pygame.draw.polygon(surface, bright, left, 2)
        pygame.draw.polygon(surface, bright, right, 2)

        # خط تیره‌ی داخلی روی هر بال
        pygame.draw.line(
            surface, dark,
            (cx - int(r * 0.6), cy - int(r * 0.3)),
            (cx - int(r * 0.85), cy + int(r * 0.2)),
            2,
        )
        pygame.draw.line(
            surface, dark,
            (cx + int(r * 0.6), cy - int(r * 0.3)),
            (cx + int(r * 0.85), cy + int(r * 0.2)),
            2,
        )

    def _draw_engines(self, surface: pygame.Surface, cx: int, cy: int, r: int) -> None:
        """دو موتور کناری با شعله‌ی زنده."""
        flicker = 0.7 + 0.3 * math.sin(self._t * 20 + 1.0)
        for sign in (-1, 1):
            ex = cx + sign * int(r * 0.5)
            ey = cy - int(r * 0.75)
            flame_len = int(r * 0.5 * flicker)

            # هاله‌ی نارنجی
            for rr in range(6, 0, -2):
                a = int(120 * (1 - rr / 6))
                if a <= 0:
                    continue
                glow = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 150, 40, a), (rr * 2, rr * 2), rr)
                surface.blit(glow, (ex - rr * 2, ey - rr * 2 - 4),
                             special_flags=pygame.BLEND_RGBA_ADD)

            # شعله
            pygame.draw.polygon(surface, (255, 140, 40), [
                (ex - int(r * 0.15), ey),
                (ex + int(r * 0.15), ey),
                (ex, ey - flame_len),
            ])
            pygame.draw.polygon(surface, (255, 230, 120), [
                (ex - int(r * 0.08), ey),
                (ex + int(r * 0.08), ey),
                (ex, ey - int(flame_len * 0.6)),
            ])

    def _draw_hull(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        base: tuple[int, int, int],
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """بدنه‌ی پیکانی رو به پایین (تهاجمی)."""
        # بدنه: شبیه نوک پیکان
        hull = [
            (cx,                 cy - int(r * 0.5)),    # بالا (پشت)
            (cx - int(r * 0.35), cy - int(r * 0.15)),   # چپ بالا
            (cx - int(r * 0.2),  cy + int(r * 0.5)),    # چپ پایین
            (cx,                 cy + int(r * 1.0)),    # نوک پایین (حمله)
            (cx + int(r * 0.2),  cy + int(r * 0.5)),    # راست پایین
            (cx + int(r * 0.35), cy - int(r * 0.15)),   # راست بالا
        ]

        # سایه (عمق)
        shadow = [(x, y + 2) for (x, y) in hull]
        pygame.draw.polygon(surface, dark, shadow)

        # بدنه
        pygame.draw.polygon(surface, base, hull)
        pygame.draw.polygon(surface, bright, hull, 2)

        # پنل روشن بالای بدنه
        top = [
            (cx,                cy - int(r * 0.4)),
            (cx - int(r * 0.2), cy - int(r * 0.1)),
            (cx + int(r * 0.2), cy - int(r * 0.1)),
        ]
        pygame.draw.polygon(surface, self._lighter(base, 30), top)

    def _draw_armor_lines(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        darker: tuple[int, int, int],
    ) -> None:
        """خطوط زره افقی روی بدنه."""
        for y_off in (-0.2, 0.1, 0.4):
            y = cy + int(r * y_off)
            w = int(r * 0.28 * (1 - y_off * 0.5))
            pygame.draw.line(
                surface, darker,
                (cx - w, y), (cx + w, y), 1,
            )

    def _draw_eye(self, surface: pygame.Surface, cx: int, cy: int, r: int) -> None:
        """چشم قرمز درخشان (تهدید)."""
        eye_y = cy + int(r * 0.1)
        eye_r = max(3, int(r * 0.18))

        # هاله‌ی قرمز
        glow_size = eye_r * 4
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -2):
            a = int(140 * (1 - rr / glow_size))
            if a <= 0:
                continue
            pygame.draw.circle(glow, (255, 40, 40, a),
                               (glow_size, glow_size), rr)
        surface.blit(glow, (cx - glow_size, eye_y - glow_size),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # خود چشم
        pygame.draw.circle(surface, (255, 40, 40), (cx, eye_y), eye_r)
        pygame.draw.circle(surface, (255, 200, 200), (cx, eye_y), max(1, eye_r // 2))
        pygame.draw.circle(surface, (255, 255, 255), (cx - 1, eye_y - 1), max(1, eye_r // 4))

    def _apply_fade(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        alpha: int,
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


__all__ = ["NormalEnemy"]
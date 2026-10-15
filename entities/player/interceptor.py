"""
entities/player/interceptor.py
==============================

سفینه‌ی INTERCEPTOR — رهگیر سریع و شکننده.

سبک بازی:
    • سریع‌ترین سفینه
    • کم‌ترین HP (۲)
    • شلیک سریع ولی ضعیف
    • مناسب بازیکن‌های تهاجمی که با فرار زنده می‌مونن

ظاهر:
    بدنه‌ی کشیده و تیز رو به جلو، بال‌های پهن پیکانی،
    دو موتور تکی کناری، رنگ آبی فیروزه‌ای.
"""

from __future__ import annotations

import pygame

from core import settings as S
from entities.bullet import BulletKind
from entities.player.base import Player


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Interceptor
# ═══════════════════════════════════════════════════════════════════════════

class Interceptor(Player):
    """رهگیر سریع — سبک، تیز، تهاجمی."""

    # ---- شناسه ----
    NAME        = "INTERCEPTOR"
    DESCRIPTION = "Fast and fragile. Outspeed them or die trying."
    KIND_KEY    = "interceptor"

    # ---- آمار (سبک و سریع) ----
    MAX_HP:        int   = 2
    SPEED:         float = 480.0       # خیلی سریع
    RADIUS:        float = 18.0        # کوچیک‌تر
    INVULN_TIME:   float = 1.8
    SHOOT_CD:      float = 0.10        # سریع شلیک
    BULLET_SPEED:  float = 900.0
    BULLET_DAMAGE: int   = 1
    BULLET_KIND:   BulletKind = BulletKind.LASER

    # فیزیک تیز و پاسخ‌گو
    ACCEL: float = 14.0
    DRAG:  float = 9.5

    # ---- رنگ‌ها ----
    PRIMARY_COLOR:   tuple[int, int, int] = (60, 220, 255)     # فیروزه‌ای
    SECONDARY_COLOR: tuple[int, int, int] = (30, 100, 160)
    ACCENT_COLOR:    tuple[int, int, int] = (255, 240, 100)    # زرد
    HIGHLIGHT_COLOR: tuple[int, int, int] = (235, 245, 255)
    FLAME_COLOR:     tuple[int, int, int] = (100, 200, 255)    # شعله‌ی آبی

    # ─────────────────────────────────────────────────────────────────────
    #  موتور: دو موتور کنار هم (نه سه‌گانه)
    # ─────────────────────────────────────────────────────────────────────

    def get_engine_offsets(self) -> list[tuple[float, float, float]]:
        return [
            (-0.45, 0.95, 0.85),
            ( 0.45, 0.95, 0.85),
        ]

    # ─────────────────────────────────────────────────────────────────────
    #  رسم بدنه — رهگیر تیز
    # ─────────────────────────────────────────────────────────────────────

    def draw_ship(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius)
        primary = self.PRIMARY_COLOR
        secondary = self.SECONDARY_COLOR
        highlight = self.HIGHLIGHT_COLOR
        accent = self.ACCENT_COLOR

        # ---- ۱. سایه‌ی زیر (عمق) ----
        shadow_pts = [
            (cx,                  cy - int(r * 1.25) + 2),
            (cx - int(r * 1.30),  cy + int(r * 0.55) + 2),
            (cx + int(r * 1.30),  cy + int(r * 0.55) + 2),
        ]
        pygame.draw.polygon(surface, (5, 30, 60), shadow_pts)

        # ---- ۲. بال‌های تیز پیکانی ----
        # بال چپ
        left_wing = [
            (cx - int(r * 0.35), cy - int(r * 0.30)),   # بالا-داخلی
            (cx - int(r * 1.30), cy + int(r * 0.15)),   # نوک چپ
            (cx - int(r * 1.10), cy + int(r * 0.55)),   # پایین-چپ
            (cx - int(r * 0.30), cy + int(r * 0.45)),   # پایین-داخلی
        ]
        # بال راست (آینه)
        right_wing = [(cx + (cx - x), y) for (x, y) in left_wing]

        pygame.draw.polygon(surface, secondary, left_wing)
        pygame.draw.polygon(surface, secondary, right_wing)
        pygame.draw.polygon(surface, primary, left_wing, 2)
        pygame.draw.polygon(surface, primary, right_wing, 2)

        # ---- ۳. خط نئونی روی بال‌ها ----
        for sign in (-1, 1):
            pygame.draw.line(
                surface, primary,
                (cx + sign * int(r * 0.55), cy - int(r * 0.1)),
                (cx + sign * int(r * 1.15), cy + int(r * 0.30)),
                1,
            )

        # ---- ۴. بدنه‌ی اصلی — کشیده و تیز ----
        hull = [
            (cx,                  cy - int(r * 1.25)),   # نوک
            (cx - int(r * 0.35),  cy - int(r * 0.20)),   # چپ بالا
            (cx - int(r * 0.45),  cy + int(r * 0.55)),   # چپ پایین
            (cx,                  cy + int(r * 0.75)),   # دنباله‌ی وسط
            (cx + int(r * 0.45),  cy + int(r * 0.55)),
            (cx + int(r * 0.35),  cy - int(r * 0.20)),
        ]
        pygame.draw.polygon(surface, primary, hull)
        pygame.draw.polygon(surface, highlight, hull, 2)

        # ---- ۵. نوار روشن مرکزی (نوک تیز) ----
        stripe = [
            (cx,                  cy - int(r * 1.15)),
            (cx - int(r * 0.15),  cy - int(r * 0.20)),
            (cx,                  cy + int(r * 0.30)),
            (cx + int(r * 0.15),  cy - int(r * 0.20)),
        ]
        pygame.draw.polygon(surface, highlight, stripe)
        # خط مرکزی نارنجی/زرد
        pygame.draw.line(
            surface, accent,
            (cx, cy - int(r * 1.05)),
            (cx, cy + int(r * 0.25)),
            2,
        )

        # ---- ۶. کابین (روی draw_ship خودمون) ----
        cab_y = cy - int(r * 0.30)
        cab_r = max(2, int(r * 0.20))
        pygame.draw.circle(surface, accent, (cx, cab_y), cab_r + 1)
        pygame.draw.circle(surface, (255, 255, 220), (cx, cab_y), cab_r)

        # ---- ۷. خطوط تزئینی روی بدنه ----
        for sign in (-1, 1):
            pygame.draw.line(
                surface, secondary,
                (cx + sign * int(r * 0.25), cy - int(r * 0.4)),
                (cx + sign * int(r * 0.30), cy + int(r * 0.5)),
                1,
            )

        # ---- ۸. رأس‌های درخشان بال‌ها ----
        for sign in (-1, 1):
            tip_x = cx + sign * int(r * 1.25)
            tip_y = cy + int(r * 0.20)
            self._draw_tip_glow(surface, tip_x, tip_y, int(r * 0.15))

        for sign in (-1, 1):
            tip_x = cx + sign * int(r * 1.25)
            tip_y = cy + int(r * 0.20)
            self._draw_tip_glow(surface, tip_x, tip_y, int(r * 0.15))

    def _draw_tip_glow(
        self,
        surface: pygame.Surface,
        x: int, y: int,
        size: int,
    ) -> None:
        """نقطه‌ی درخشان روی رأس بال (نئون)."""
        size = max(2, size)
        accent = self.ACCENT_COLOR

        # هاله
        glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        for rr in range(size * 2, 0, -1):
            a = int(120 * (1 - rr / (size * 2)))
            if a <= 0:
                continue
            pygame.draw.circle(glow, (*accent, a), (size * 2, size * 2), rr)
        surface.blit(
            glow, (x - size * 2, y - size * 2),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # نقطه‌ی مرکزی
        pygame.draw.circle(surface, (255, 255, 255), (x, y), max(1, size // 2))


__all__ = ["Interceptor"]

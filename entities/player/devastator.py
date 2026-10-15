"""
entities/player/devastator.py
=============================

سفینه‌ی DEVASTATOR — ویرانگر سنگین با سلاح پلاسما.

سبک بازی:
    • شلیک پلاسما (گلوله‌ی درشت، آسیب ۲)
    • HP زیاد (۴)
    • سرعت پایین (۲۹۰)
    • شلیک کند ولی هر گلوله دو برابر آسیب می‌زنه
    • مناسب بازیکن‌هایی که می‌خوان هر ضربه حساب بشه

ظاهر:
    بدنه‌ی حجیم و صنعتی با خطوط قرمز،
    دو توپ بزرگ شلیک پلاسما،
    هسته‌ی نارنجی درخشان در مرکز،
    رنگ قرمز-نارنجی-خاکستری.
"""

from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.bullet import BulletKind
from entities.player.base import Player


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Devastator
# ═══════════════════════════════════════════════════════════════════════════

class Devastator(Player):
    """ویرانگر — کند، سنگین، پرقدرت."""

    # ---- شناسه ----
    NAME        = "DEVASTATOR"
    DESCRIPTION = "Every shot is a statement. Make them count."
    KIND_KEY    = "devastator"

    # ---- آمار (سنگین و پرقدرت) ----
    MAX_HP:        int   = 4
    SPEED:         float = 290.0
    RADIUS:        float = 24.0        # بزرگ
    INVULN_TIME:   float = 1.5
    SHOOT_CD:      float = 0.32        # کند
    BULLET_SPEED:  float = 620.0
    BULLET_DAMAGE: int   = 2           # آسیب دوگانه
    BULLET_KIND:   BulletKind = BulletKind.PLASMA  # گلوله‌ی درشت نارنجی

    # فیزیک سنگین (شتاب کم، میرایی زیاد — حس تانک)
    ACCEL: float = 5.5
    DRAG:  float = 6.0

    # ---- رنگ‌ها ----
    PRIMARY_COLOR:   tuple[int, int, int] = (230, 90, 60)      # قرمز-نارنجی
    SECONDARY_COLOR: tuple[int, int, int] = (90, 40, 30)
    ACCENT_COLOR:    tuple[int, int, int] = (255, 200, 60)     # طلایی
    HIGHLIGHT_COLOR: tuple[int, int, int] = (255, 230, 200)    # کرم
    FLAME_COLOR:     tuple[int, int, int] = (255, 130, 30)

    # ─────────────────────────────────────────────────────────────────────
    #  الگوی شلیک: تک گلوله‌ی سنگین
    # ─────────────────────────────────────────────────────────────────────

    def _get_shot_angles(self) -> list[float]:
        """
        Devastator گلوله‌ی سنگین شلیک می‌کنه (یکی، از مرکز).
        با پاورآپ، سه‌گانه سنگین.
        """
        if self.powerup_time > 0.0:
            return [-105.0, -90.0, -75.0]
        return [-90.0]

    # ─────────────────────────────────────────────────────────────────────
    #  شعله‌های موتور: دو تا بزرگ کناری (صنعتی)
    # ─────────────────────────────────────────────────────────────────────

    def get_engine_offsets(self) -> list[tuple[float, float, float]]:
        return [
            (-0.60, 0.90, 1.10),
            ( 0.60, 0.90, 1.10),
        ]

    # ─────────────────────────────────────────────────────────────────────
    #  رسم بدنه — ویرانگر صنعتی
    # ─────────────────────────────────────────────────────────────────────

    def draw_ship(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius)
        primary = self.PRIMARY_COLOR
        secondary = self.SECONDARY_COLOR
        highlight = self.HIGHLIGHT_COLOR
        accent = self.ACCENT_COLOR

        # ---- ۱. سایه‌ی زیر (عمق) ----
        shadow = [
            (cx - int(r * 0.95), cy - int(r * 0.75) + 2),
            (cx - int(r * 1.05), cy + int(r * 0.70) + 2),
            (cx + int(r * 1.05), cy + int(r * 0.70) + 2),
            (cx + int(r * 0.95), cy - int(r * 0.75) + 2),
        ]
        pygame.draw.polygon(surface, (40, 10, 5), shadow)

        # ---- ۲. بال‌های مربعی زره‌ای ----
        for sign in (-1, 1):
            wing = [
                (cx + sign * int(r * 0.55), cy - int(r * 0.70)),
                (cx + sign * int(r * 1.20), cy - int(r * 0.55)),
                (cx + sign * int(r * 1.20), cy + int(r * 0.35)),
                (cx + sign * int(r * 0.95), cy + int(r * 0.65)),
                (cx + sign * int(r * 0.45), cy + int(r * 0.50)),
            ]
            pygame.draw.polygon(surface, secondary, wing)
            pygame.draw.polygon(surface, primary, wing, 2)

            # خط افقی روی بال
            pygame.draw.line(
                surface, accent,
                (cx + sign * int(r * 0.65), cy - int(r * 0.10)),
                (cx + sign * int(r * 1.15), cy - int(r * 0.10)),
                2,
            )

        # ---- ۳. پادهای سلاح بزرگ (توپ‌های پلاسما) ----
        for sign in (-1, 1):
            pod_x = cx + sign * int(r * 0.75)
            pod_y = cy - int(r * 0.15)
            pod_w = max(5, int(r * 0.25))
            pod_h = max(7, int(r * 0.35))

            # بدنه‌ی توپ
            rect = pygame.Rect(
                pod_x - pod_w, pod_y - pod_h // 2,
                pod_w * 2, pod_h,
            )
            pygame.draw.rect(surface, secondary, rect)
            pygame.draw.rect(surface, primary, rect, 2)

            # دهانه‌ی توپ (دایره‌ی درخشان)
            tip_y = pod_y - pod_h // 2 - 2
            # هاله‌ی نارنجی
            glow = pygame.Surface((20, 20), pygame.SRCALPHA)
            for rr in range(10, 0, -2):
                a = int(120 * (1 - rr / 10))
                if a <= 0:
                    continue
                pygame.draw.circle(glow, (255, 180, 60, a), (10, 10), rr)
            surface.blit(glow, (pod_x - 10, tip_y - 10),
                         special_flags=pygame.BLEND_RGBA_ADD)

            # دایره‌ی توپ
            pygame.draw.circle(surface, (255, 130, 60), (pod_x, tip_y), max(3, int(r * 0.10)))
            pygame.draw.circle(surface, (255, 240, 180), (pod_x, tip_y), max(1, int(r * 0.05)))

        # ---- ۴. بدنه‌ی اصلی — حجیم و ذوزنقه‌ای ----
        hull = [
            (cx,                  cy - int(r * 1.00)),   # بالا
            (cx - int(r * 0.50),  cy - int(r * 0.65)),   # چپ بالا
            (cx - int(r * 0.65),  cy + int(r * 0.55)),   # چپ پایین
            (cx,                  cy + int(r * 0.90)),   # دنباله
            (cx + int(r * 0.65),  cy + int(r * 0.55)),
            (cx + int(r * 0.50),  cy - int(r * 0.65)),
        ]
        pygame.draw.polygon(surface, primary, hull)
        pygame.draw.polygon(surface, highlight, hull, 2)

        # ---- ۵. لایه‌ی میانی روشن‌تر ----
        inner = [
            (cx,                  cy - int(r * 0.85)),
            (cx - int(r * 0.35),  cy - int(r * 0.45)),
            (cx - int(r * 0.40),  cy + int(r * 0.35)),
            (cx,                  cy + int(r * 0.65)),
            (cx + int(r * 0.40),  cy + int(r * 0.35)),
            (cx + int(r * 0.35),  cy - int(r * 0.45)),
        ]
        pygame.draw.polygon(surface, (250, 130, 90), inner)

        # ---- ۶. خطوط زره افقی ----
        for y_off in (-0.35, 0.10, 0.45):
            y = cy + int(r * y_off)
            w = int(r * 0.55)
            pygame.draw.line(surface, accent,
                             (cx - w, y), (cx + w, y), 1)

        # ---- ۷. خط عمودی میانی (شکاف) ----
        pygame.draw.line(
            surface, secondary,
            (cx, cy - int(r * 0.80)),
            (cx, cy + int(r * 0.85)),
            2,
        )

        # ---- ۸. هسته‌ی نارنجی پالسی (قلب ویرانگر) ----
        self._draw_reactor_core(surface, cx, cy, r)

        # ---- ۹. کابین کوچک مستطیلی (صنعتی) ----
        cab_y = cy - int(r * 0.45)
        cab_w = max(4, int(r * 0.22))
        cab_h = max(3, int(r * 0.12))
        cab_rect = pygame.Rect(
            cx - cab_w, cab_y - cab_h,
            cab_w * 2, cab_h * 2,
        )
        pygame.draw.rect(surface, secondary, cab_rect)
        pygame.draw.rect(surface, highlight, cab_rect, 2)
        pygame.draw.rect(surface, accent, cab_rect.inflate(-2, -2))

        # ---- ۱۰. چراغ‌های هشدار (قرمز چشمک‌زن) ----
        blink = 0.5 + 0.5 * math.sin(self._t * 6.0)
        for sign in (-1, 1):
            tip_x = cx + sign * int(r * 1.10)
            tip_y = cy + int(r * 0.45)
            alpha = int(200 * blink)
            if alpha <= 0:
                continue
            glow = pygame.Surface((14, 14), pygame.SRCALPHA)
            for rr in range(7, 0, -2):
                a = int(alpha * (1 - rr / 7))
                if a <= 0:
                    continue
                pygame.draw.circle(glow, (255, 60, 60, a), (7, 7), rr)
            surface.blit(glow, (tip_x - 7, tip_y - 7),
                         special_flags=pygame.BLEND_RGBA_ADD)
            pygame.draw.circle(surface, (255, 100, 100), (tip_x, tip_y), 3)

    # ─────────────────────────────────────────────────────────────────────
    #  راکتور مرکزی
    # ─────────────────────────────────────────────────────────────────────

    def _draw_reactor_core(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هسته‌ی نارنجی درخشان با پالس سریع."""
        pulse = 0.7 + 0.3 * math.sin(self._t * 7.0)
        core_r = max(3, int(r * 0.22 * pulse))
        core_y = cy + int(r * 0.05)

        # هاله‌ی نارنجی
        glow_size = int(r * 0.55)
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -1):
            a = int(160 * (1 - rr / glow_size) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (255, 160, 60, a),
                               (glow_size, glow_size), rr)
        surface.blit(
            glow, (cx - glow_size, core_y - glow_size),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # هسته
        pygame.draw.circle(surface, (255, 200, 120), (cx, core_y), core_r)
        pygame.draw.circle(surface, (255, 255, 220), (cx, core_y), max(1, core_r // 2))

        # حلقه‌ی چرخان دور هسته
        ring_r = int(r * 0.35)
        for i in range(4):
            a = self._t * 3.0 + i * math.pi / 2
            px = cx + int(math.cos(a) * ring_r)
            py = core_y + int(math.sin(a) * ring_r * 0.6)
            pygame.draw.circle(surface, (255, 180, 80), (px, py), 2)


__all__ = ["Devastator"]
"""
entities/player/phantom.py
==========================

سفینه‌ی PHANTOM — شبح متعادل با قدرت جادویی.

سبک بازی:
    • آمار متعادل (سرعت، جان، شلیک)
    • پاورآپ‌ها مدت بیشتری دوام میارن (۲ برابر)
    • شلیک سه‌گانه از ابتدا (بدون نیاز به پاورآپ)
    • مناسب بازیکن‌هایی که می‌خوان تعادل و قدرت داشته باشن

ظاهر:
    بدنه‌ی الماسی کشیده با خطوط نئونی بنفش،
    حلقه‌ی چرخان دور کابین،
    هسته‌ی درخشان پالسی در مرکز،
    رنگ‌های بنفش-صورتی جادویی.
"""

from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.bullet import BulletKind
from entities.player.base import Player


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس Phantom
# ═══════════════════════════════════════════════════════════════════════════

class Phantom(Player):
    """شبح — متعادل، مرموز، با پاورآپ‌های تقویت‌شده."""

    # ---- شناسه ----
    NAME        = "PHANTOM"
    DESCRIPTION = "Balanced power with a taste of the void."
    KIND_KEY    = "phantom"

    # ---- آمار (متعادل) ----
    MAX_HP:        int   = 2
    SPEED:         float = 360.0       # متوسط-سریع
    RADIUS:        float = 20.0        # متوسط
    INVULN_TIME:   float = 1.7
    SHOOT_CD:      float = 0.18        # کمی سریع‌تر از معمولی
    BULLET_SPEED:  float = 800.0
    BULLET_DAMAGE: int   = 1
    BULLET_KIND:   BulletKind = BulletKind.PLAYER

    # فیزیک روان و متعادل
    ACCEL: float = 10.0
    DRAG:  float = 8.0

    # ---- رنگ‌ها ----
    PRIMARY_COLOR:   tuple[int, int, int] = (190, 90, 255)     # بنفش
    SECONDARY_COLOR: tuple[int, int, int] = (70, 30, 130)
    ACCENT_COLOR:    tuple[int, int, int] = (255, 90, 200)     # صورتی
    HIGHLIGHT_COLOR: tuple[int, int, int] = (240, 210, 255)    # یاسی روشن
    FLAME_COLOR:     tuple[int, int, int] = (200, 100, 255)    # شعله‌ی بنفش

    # ---- ویژگی خاص: پاورآپ ۲ برابر ----
    POWERUP_MULTIPLIER: float = 1.5

    # ─────────────────────────────────────────────────────────────────────
    #  الگوی شلیک: سه‌گانه از ابتدا
    # ─────────────────────────────────────────────────────────────────────
    def grant_rapid_fire(self, duration: float) -> None:
        super().grant_rapid_fire(duration * self.POWERUP_MULTIPLIER)

    def _get_shot_angles(self) -> list[float]:
        """
        Phantom از ابتدا شلیک سه‌گانه داره (بدون نیاز به پاورآپ).
        با پاورآپ، پنج‌گانه می‌شه.
        """
        if self.powerup_time > 0.0:
            # پنج‌گانه
            return [-110.0, -100.0, -90.0, -80.0, -70.0]
        # سه‌گانه (پیش‌فرض)
        return [-102.0, -90.0, -78.0]

    # ─────────────────────────────────────────────────────────────────────
    #  پاورآپ با دوام بیشتر
    # ─────────────────────────────────────────────────────────────────────

    def grant_powerup(self, duration=None) -> None:
        """Phantom پاورآپ‌ها رو ۲ برابر دریافت می‌کنه."""
        d = S.PowerupCfg.DURATION if duration is None else duration
        self.powerup_time = d * self.POWERUP_MULTIPLIER

    # ─────────────────────────────────────────────────────────────────────
    #  موتورها: یک موتور بزرگ مرکزی + دو موتور کوچیک
    # ─────────────────────────────────────────────────────────────────────

    def get_engine_offsets(self) -> list[tuple[float, float, float]]:
        return [
            (-0.35, 1.00, 0.60),
            ( 0.00, 1.10, 0.95),
            ( 0.35, 1.00, 0.60),
        ]

    # ─────────────────────────────────────────────────────────────────────
    #  رسم بدنه — شبح جادویی
    # ─────────────────────────────────────────────────────────────────────

    def draw_ship(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        r = int(self.radius)
        primary = self.PRIMARY_COLOR
        secondary = self.SECONDARY_COLOR
        highlight = self.HIGHLIGHT_COLOR
        accent = self.ACCENT_COLOR

        # ---- ۲. سایه‌ی زیر (عمق) ----
        shadow = [
            (cx,                  cy - int(r * 1.20) + 2),
            (cx - int(r * 0.95),  cy + int(r * 0.30) + 2),
            (cx,                  cy + int(r * 0.85) + 2),
            (cx + int(r * 0.95),  cy + int(r * 0.30) + 2),
        ]
        pygame.draw.polygon(surface, (30, 10, 50), shadow)

        # ---- ۳. بال‌های مورب (الماسی) ----
        # بال چپ
        left_wing = [
            (cx - int(r * 0.40), cy - int(r * 0.50)),   # بالا-داخلی
            (cx - int(r * 1.15), cy - int(r * 0.05)),   # نوک چپ (الماسی)
            (cx - int(r * 1.00), cy + int(r * 0.55)),   # پایین-چپ
            (cx - int(r * 0.30), cy + int(r * 0.35)),   # پایین-داخلی
        ]
        right_wing = [(cx + (cx - x), y) for (x, y) in left_wing]

        pygame.draw.polygon(surface, secondary, left_wing)
        pygame.draw.polygon(surface, secondary, right_wing)
        pygame.draw.polygon(surface, primary, left_wing, 2)
        pygame.draw.polygon(surface, primary, right_wing, 2)

        # ---- ۴. حلقه‌ی چرخان دور بال‌ها (افکت جادویی) ----
        self._draw_rotating_wing_dots(surface, cx, cy, r)

        # ---- ۵. بدنه‌ی اصلی — الماس کشیده ----
        hull = [
            (cx,                  cy - int(r * 1.20)),   # نوک بالا
            (cx - int(r * 0.55),  cy - int(r * 0.20)),   # چپ
            (cx - int(r * 0.45),  cy + int(r * 0.60)),   # پایین-چپ
            (cx,                  cy + int(r * 0.85)),   # دنباله
            (cx + int(r * 0.45),  cy + int(r * 0.60)),
            (cx + int(r * 0.55),  cy - int(r * 0.20)),
        ]
        pygame.draw.polygon(surface, primary, hull)
        pygame.draw.polygon(surface, highlight, hull, 2)

        # ---- ۶. لایه‌ی داخلی (بدنه‌ی روشن‌تر) ----
        inner = [
            (cx,                  cy - int(r * 1.05)),
            (cx - int(r * 0.30),  cy - int(r * 0.15)),
            (cx - int(r * 0.25),  cy + int(r * 0.45)),
            (cx,                  cy + int(r * 0.65)),
            (cx + int(r * 0.25),  cy + int(r * 0.45)),
            (cx + int(r * 0.30),  cy - int(r * 0.15)),
        ]
        pygame.draw.polygon(surface, (220, 140, 255), inner)

        # ---- ۷. خطوط نئونی مورب روی بدنه ----
        for sign in (-1, 1):
            pygame.draw.line(
                surface, accent,
                (cx + sign * int(r * 0.45), cy - int(r * 0.30)),
                (cx + sign * int(r * 0.20), cy + int(r * 0.55)),
                1,
            )

        # ---- ۸. هسته‌ی درخشان پالسی (قلب شبح) ----
        self._draw_pulsing_core(surface, cx, cy, r)

        # ---- ۹. کابین (نقاب شبح) ----
        self._draw_phantom_face(surface, cx, cy, r)

        # ---- ۱۰. رأس‌های درخشان الماسی ----
        for (vx, vy) in [(cx, cy - int(r * 1.20)),
                         (cx - int(r * 0.55), cy - int(r * 0.20)),
                         (cx + int(r * 0.55), cy - int(r * 0.20))]:
            self._draw_vertex_glow(surface, vx, vy, int(r * 0.10), accent)

    # ─────────────────────────────────────────────────────────────────────
    #  اجزای اختصاصی Phantom
    # ─────────────────────────────────────────────────────────────────────

    def _draw_magic_aura(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هاله‌ی بنفش پالسی دور بدنه."""
        aura_r = int(r * 1.5)
        pulse = 0.85 + 0.15 * math.sin(self._t * 3.0)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -3):
            a = int(35 * (1 - rr / aura_r) ** 1.5 * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(aura, (190, 90, 255, a), (aura_r, aura_r), rr)
        surface.blit(
            aura, (cx - aura_r, cy - aura_r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    def _draw_rotating_wing_dots(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """نقاط درخشان چرخان روی لبه‌ی بال‌ها."""
        num = 6
        radius = r * 1.05
        for i in range(num):
            angle = (i / num) * math.tau + self._t * 1.5
            px = cx + int(math.cos(angle) * radius)
            py = cy + int(math.sin(angle) * radius * 0.7)
            size = 2
            a = 0.5 + 0.5 * math.sin(self._t * 4.0 + i * 0.8)
            alpha = int(100 + 120 * a)
            dot = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            pygame.draw.circle(dot, (255, 150, 255, alpha),
                               (size * 2, size * 2), size * 2)
            surface.blit(
                dot, (px - size * 2, py - size * 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    def _draw_pulsing_core(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هسته‌ی درخشان مرکزی با پالس."""
        pulse = 0.7 + 0.3 * math.sin(self._t * 5.0)
        core_r = max(3, int(r * 0.22 * pulse))
        core_y = cy - int(r * 0.10)

        # هاله
        glow_size = int(r * 0.5)
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -1):
            a = int(160 * (1 - rr / glow_size) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (255, 180, 255, a),
                               (glow_size, glow_size), rr)
        surface.blit(
            glow, (cx - glow_size, core_y - glow_size),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # هسته
        pygame.draw.circle(surface, (255, 220, 255), (cx, core_y), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, core_y), max(1, core_r // 2))

    def _draw_phantom_face(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """نقاب شبح: دو چشم درخشان."""
        face_y = cy - int(r * 0.15)
        eye_y = face_y
        eye_offset = int(r * 0.18)
        eye_r = max(2, int(r * 0.09))

        # دو چشم درخشان صورتی
        for sign in (-1, 1):
            ex = cx + sign * eye_offset
            # هاله‌ی چشم
            glow = pygame.Surface((eye_r * 6, eye_r * 6), pygame.SRCALPHA)
            for rr in range(eye_r * 3, 0, -1):
                a = int(100 * (1 - rr / (eye_r * 3)))
                if a <= 0:
                    continue
                pygame.draw.circle(glow, (255, 150, 255, a),
                                   (eye_r * 3, eye_r * 3), rr)
            surface.blit(
                glow, (ex - eye_r * 3, eye_y - eye_r * 3),
                special_flags=pygame.BLEND_RGBA_ADD,
            )
            # خود چشم
            pygame.draw.circle(surface, (255, 220, 255), (ex, eye_y), eye_r)
            pygame.draw.circle(surface, (255, 80, 200), (ex, eye_y), max(1, eye_r - 1))

    def _draw_vertex_glow(
        self,
        surface: pygame.Surface,
        x: int, y: int, size: int,
        color: tuple[int, int, int],
    ) -> None:
        """نقطه‌ی درخشان روی رأس بدنه."""
        size = max(2, size)
        glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        for rr in range(size * 2, 0, -1):
            a = int(120 * (1 - rr / (size * 2)))
            if a <= 0:
                continue
            pygame.draw.circle(glow, (*color, a), (size * 2, size * 2), rr)
        surface.blit(
            glow, (x - size * 2, y - size * 2),
            special_flags=pygame.BLEND_RGBA_ADD,
        )
        pygame.draw.circle(surface, (255, 255, 255), (x, y), max(1, size // 2))


__all__ = ["Phantom"]
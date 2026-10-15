"""
entities/enemies/normal.py
==========================

دشمن نوع اول — Normal (زنبور مهاجم).

طراحی:
    یک رهگیر سبک و سریع با سیلوئت واضح که در اندازه‌های کوچک هم
    به‌راحتی قابل تشخیص است. الهام‌گرفته از زنبور مهاجم:
        • بال‌های پهن و تیز بیرون‌زده
        • دو پاد سلاح درخشان روی بال‌ها
        • بدنه‌ی کشیده با پنل روشن
        • چشم قرمز درخشان در مرکز
        • دو موتور نارنجی درخشان در بالا

رفتار:
    • سریع‌ترین دشمن
    • یک ضربه و نابود (HP=1)
    • بدون شلیک
    • امتیاز کم، افت پاورآپ کم
"""

from __future__ import annotations

import pygame

from core import settings as S
from entities.enemies.base import Enemy, EnemyKind


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس NormalEnemy
# ═══════════════════════════════════════════════════════════════════════════

class NormalEnemy(Enemy):
    """رهگیر سبک و سریع — زنبور مهاجم."""

    KIND = EnemyKind.NORMAL

    HP          = S.EnemyCfg.Normal.HP
    RADIUS      = S.EnemyCfg.Normal.RADIUS
    SPEED       = S.EnemyCfg.Normal.SPEED
    SCORE       = S.EnemyCfg.Normal.SCORE
    DROP_CHANCE = S.EnemyCfg.Normal.DROP_CHANCE
    BODY_COLOR  = S.Palette.ENEMY_NORMAL

    # ─────────────────────────────────────────────────────────────────────
    #  منطق حرکت
    # ─────────────────────────────────────────────────────────────────────

    def update_ai(self, dt: float) -> None:
        """حرکت مستقیم به پایین با سرعت کامل."""
        self.y += self.SPEED * dt

    # ─────────────────────────────────────────────────────────────────────
    #  رسم — زنبور مهاجم
    # ─────────────────────────────────────────────────────────────────────

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = max(4, int(self.radius))
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 110)
        bright = self._lighter(base, 70)

        # ---- ۱. موتورهای پشت ----
        self._draw_engines(surface, cx, cy, r)

        # ---- ۲. بال‌های تیز بیرونی ----
        self._draw_wings(surface, cx, cy, r, dark, bright)

        # ---- ۳. پادهای سلاح ----
        self._draw_weapon_pods(surface, cx, cy, r, dark, bright)

        # ---- ۴. بدنه‌ی اصلی ----
        self._draw_hull(surface, cx, cy, r, base, dark, bright)

        # ---- ۵. چشم درخشان ----
        self._draw_eye(surface, cx, cy, r)

        # ---- ۶. خطوط تزئینی روی بدنه ----
        self._draw_panel_lines(surface, cx, cy, r, bright)

        # ---- ۷. فید در زمان ورود ----
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    # ─────────────────────────────────────────────────────────────────────
    #  اجزای رسم
    # ─────────────────────────────────────────────────────────────────────

    def _draw_engines(self, surface: pygame.Surface, cx: int, cy: int, r: int) -> None:
        """دو موتور درخشان در بالای سفینه."""
        for sign in (-1, 1):
            ex = cx + sign * int(r * 0.30)
            ey = cy - int(r * 0.85)

            # هاله
            for rr in range(4, 0, -1):
                a = int(110 * (1 - rr / 4))
                if a <= 0:
                    continue
                glow = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 180, 80, a), (rr * 2, rr * 2), rr)
                surface.blit(
                    glow, (ex - rr * 2, ey - rr * 2),
                    special_flags=pygame.BLEND_RGBA_ADD,
                )

            # نقطه‌ی مرکزی
            pygame.draw.circle(surface, (255, 240, 180), (ex, ey), max(1, int(r * 0.10)))

    def _draw_wings(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """بال‌های پهن و تیز دو طرف."""
        left = [
            (cx - int(r * 0.30), cy - int(r * 0.55)),   # بالا-داخلی
            (cx - r,             cy - int(r * 0.20)),   # نوک بالا
            (cx - int(r * 0.85), cy + int(r * 0.45)),   # نوک پایین
            (cx - int(r * 0.30), cy + int(r * 0.30)),   # پایین-داخلی
        ]
        right = [(cx + (cx - x), y) for (x, y) in left]

        pygame.draw.polygon(surface, dark, left)
        pygame.draw.polygon(surface, dark, right)
        pygame.draw.polygon(surface, bright, left, 2)
        pygame.draw.polygon(surface, bright, right, 2)

    def _draw_weapon_pods(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """دو پاد سلاح درخشان روی بال‌ها."""
        for sign in (-1, 1):
            px = cx + sign * int(r * 0.85)
            py = cy + int(r * 0.10)

            pod_w = max(3, int(r * 0.20))
            pod_h = max(4, int(r * 0.30))
            pod_rect = pygame.Rect(px - pod_w, py - pod_h, pod_w * 2, pod_h * 2)

            # بدنه‌ی پاد
            pygame.draw.rect(surface, dark, pod_rect)
            pygame.draw.rect(surface, bright, pod_rect, 1)

            # نور نارنجی
            pygame.draw.circle(surface, (255, 150, 40), (px, py), max(2, int(r * 0.12)))
            pygame.draw.circle(surface, (255, 240, 180), (px, py), max(1, int(r * 0.06)))

    def _draw_hull(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        base: tuple[int, int, int],
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """بدنه‌ی مرکزی کشیده به سمت پایین."""
        hull = [
            (cx,                  cy - int(r * 0.65)),   # بالا
            (cx - int(r * 0.42),  cy - int(r * 0.35)),   # بالا-چپ
            (cx - int(r * 0.50),  cy + int(r * 0.30)),   # چپ میانی
            (cx,                  cy + int(r * 1.00)),   # نوک پایین
            (cx + int(r * 0.50),  cy + int(r * 0.30)),   # راست میانی
            (cx + int(r * 0.42),  cy - int(r * 0.35)),   # بالا-راست
        ]

        # سایه (عمق بصری)
        shadow = [(x, y + 2) for (x, y) in hull]
        pygame.draw.polygon(surface, dark, shadow)

        # بدنه
        pygame.draw.polygon(surface, base, hull)

        # پنل روشن بالای بدنه
        top_panel = [
            (cx,                 cy - int(r * 0.55)),
            (cx - int(r * 0.25), cy - int(r * 0.25)),
            (cx + int(r * 0.25), cy - int(r * 0.25)),
        ]
        pygame.draw.polygon(surface, bright, top_panel)

        # خط نئونی دور
        pygame.draw.polygon(surface, (255, 255, 255), hull, 2)

    def _draw_eye(self, surface: pygame.Surface, cx: int, cy: int, r: int) -> None:
        """چشم قرمز درخشان در مرکز."""
        eye_y = cy + int(r * 0.05)
        eye_r = max(3, int(r * 0.20))

        # هاله
        glow_size = eye_r * 3
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -2):
            a = int(150 * (1 - rr / glow_size))
            if a <= 0:
                continue
            pygame.draw.circle(glow, (255, 80, 80, a), (glow_size, glow_size), rr)
        surface.blit(
            glow, (cx - glow_size, eye_y - glow_size),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # چشم
        pygame.draw.circle(surface, (255, 40, 40), (cx, eye_y), eye_r)
        pygame.draw.circle(surface, (255, 200, 200), (cx, eye_y), max(1, int(eye_r * 0.5)))
        pygame.draw.circle(surface, (255, 255, 255), (cx - 1, eye_y - 1), max(1, int(eye_r * 0.25)))

    def _draw_panel_lines(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        bright: tuple[int, int, int],
    ) -> None:
        """خطوط تزئینی کناری روی بدنه."""
        for sign in (-1, 1):
            pygame.draw.line(
                surface, bright,
                (cx + sign * int(r * 0.30), cy - int(r * 0.15)),
                (cx + sign * int(r * 0.20), cy + int(r * 0.55)),
                1,
            )

    def _apply_fade(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        alpha: int,
    ) -> None:
        """پوشش نیمه‌شفاف سیاه برای انیمیشن ورود."""
        a = 255 - alpha
        if a <= 0:
            return
        fade = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        fade.fill((0, 0, 0, int(a * 0.7)))
        surface.blit(fade, (cx - r * 2, cy - r * 2))

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی‌های رنگ
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _darker(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        return (max(0, c[0] - amount), max(0, c[1] - amount), max(0, c[2] - amount))

    @staticmethod
    def _lighter(c: tuple[int, int, int], amount: int) -> tuple[int, int, int]:
        return (min(255, c[0] + amount), min(255, c[1] + amount), min(255, c[2] + amount))


__all__ = ["NormalEnemy"]
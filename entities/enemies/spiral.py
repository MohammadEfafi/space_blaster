"""
entities/enemies/spiral.py
==========================

دشمن نوع سوم — Spiral (کریستال چرخان).

طراحی:
    یک دشمن اسرارآمیز و شناور که با حرکت سینوسی مسیرش غیرقابل پیش‌بینی
    است. الهام‌گرفته از کریستال‌های فضایی:
        • بدنه‌ی ستاره‌ای شش‌پر که می‌چرخد
        • هاله‌ی سبز درخشان به عنوان aura مرکزی
        • هسته‌ی درخشان با پالس
        • دنباله‌ی ذرات که پشتش رها می‌شود
        • خطوط انرژی از مرکز به سمت رأس‌ها

رفتار:
    • حرکت سینوسی افقی (غیرقابل پیش‌بینی)
    • چرخش مداوم بدنه
    • HP متوسط (2)
    • بدون شلیک، ولی سریع
"""

from __future__ import annotations

import math
import random
import pygame

from core import settings as S
from entities.enemies.base import Enemy, EnemyKind


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس SpiralEnemy
# ═══════════════════════════════════════════════════════════════════════════

class SpiralEnemy(Enemy):
    """کریستال چرخان — سریع، غیرقابل پیش‌بینی، اسرارآمیز."""

    KIND = EnemyKind.SPIRAL

    HP          = S.EnemyCfg.Spiral.HP
    RADIUS      = S.EnemyCfg.Spiral.RADIUS
    SPEED       = S.EnemyCfg.Spiral.SPEED
    SCORE       = S.EnemyCfg.Spiral.SCORE
    DROP_CHANCE = S.EnemyCfg.Spiral.DROP_CHANCE
    AMPLITUDE   = S.EnemyCfg.Spiral.AMPLITUDE
    FREQUENCY   = S.EnemyCfg.Spiral.FREQUENCY
    BODY_COLOR  = S.Palette.ENEMY_SPIRAL

    # ─────────────────────────────────────────────────────────────────────
    #  پیکربندی اختصاصی
    # ─────────────────────────────────────────────────────────────────────

    def _configure(self) -> None:
        # فاز تصادفی برای اینکه هر اسپیرال جای مختلفی شروع کنه
        self._phase: float = random.uniform(0, math.tau)
        # زاویه‌ی چرخش فعلی
        self._rotation: float = random.uniform(0, 360)
        # سرعت چرخش (تصادفی، ولی همیشه مثبت)
        self._rotation_speed: float = random.uniform(90, 150)

    # ─────────────────────────────────────────────────────────────────────
    #  منطق حرکت
    # ─────────────────────────────────────────────────────────────────────

    def update_ai(self, dt: float) -> None:
        """حرکت سینوسی افقی + چرخش مداوم."""
        # حرکت عمودی
        self.y += self.SPEED * dt
        # حرکت سینوسی افقی
        self.x = self._base_x + math.sin(
            self._t * self.FREQUENCY + self._phase
        ) * self.AMPLITUDE
        # چرخش
        self._rotation = (self._rotation + self._rotation_speed * dt) % 360

    # ─────────────────────────────────────────────────────────────────────
    #  رسم — کریستال چرخان
    # ─────────────────────────────────────────────────────────────────────

    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        r = max(5, int(self.radius))
        cx, cy = int(self.x), int(self.y)

        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        bright = self._lighter(base, 80)

        # ---- ۱. هاله‌ی بیرونی (aura) ----
        self._draw_aura(surface, cx, cy, r)

        # ---- ۲. ستاره‌ی بیرونی (۶ پر) ----
        outer_pts, inner_pts = self._compute_star_points(cx, cy, r)

        # سایه
        pygame.draw.polygon(surface, dark, outer_pts)
        # بدنه
        pygame.draw.polygon(surface, base, outer_pts)
        # خط نئونی
        pygame.draw.polygon(surface, bright, outer_pts, 2)

        # ---- ۳. ستاره‌ی داخلی (کوچک‌تر، چرخش مخالف) ----
        inner_outer, inner_inner = self._compute_star_points(
            cx, cy, int(r * 0.55),
            rotation_offset=-30.0,  # چرخش مخالف برای تضاد
        )
        pygame.draw.polygon(surface, dark, inner_outer)
        pygame.draw.polygon(surface, bright, inner_outer, 1)

        # ---- ۴. خطوط انرژی از مرکز به رأس‌ها ----
        self._draw_energy_lines(surface, cx, cy, r, bright)

        # ---- ۵. هسته‌ی درخشان ----
        self._draw_core(surface, cx, cy, r)

        # ---- ۶. رأس‌های درخشان ----
        self._draw_vertex_glows(surface, outer_pts, r)

        # ---- ۷. دنباله‌ی ذرات ----
        self._draw_trail(surface, cx, cy, r)

        # ---- ۸. فید ورود ----
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)

    # ─────────────────────────────────────────────────────────────────────
    #  محاسبه‌ی نقاط ستاره
    # ─────────────────────────────────────────────────────────────────────

    def _compute_star_points(
        self,
        cx: int, cy: int, r: float,
        rotation_offset: float = 0.0,
    ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        """
        نقاط ستاره‌ی شش‌پر (۱۲ نقطه: ۶ بیرونی + ۶ داخلی) رو محاسبه می‌کنه.
        rotation_offset درجه‌ی اضافی روی چرخش اعمال می‌کنه.
        """
        outer: list[tuple[float, float]] = []
        inner: list[tuple[float, float]] = []

        rot_rad = math.radians(self._rotation + rotation_offset)
        num_points = 6

        for i in range(num_points):
            # نقطه‌ی بیرونی
            a_out = rot_rad + (i / num_points) * math.tau
            outer.append((
                cx + math.cos(a_out) * r,
                cy + math.sin(a_out) * r,
            ))
            # نقطه‌ی داخلی (بین دو بیرونی)
            a_in = a_out + math.pi / num_points
            inner.append((
                cx + math.cos(a_in) * r * 0.45,
                cy + math.sin(a_in) * r * 0.45,
            ))

        # ترکیب: بیرونی → داخلی → بیرونی → ...
        star = []
        for i in range(num_points):
            star.append(outer[i])
            star.append(inner[i])

        return star, inner

    # ─────────────────────────────────────────────────────────────────────
    #  اجزای رسم
    # ─────────────────────────────────────────────────────────────────────

    def _draw_aura(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هاله‌ی سبز نرم پشت کریستال."""
        aura_r = int(r * 1.6)
        if aura_r <= 0:
            return
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        # پالس ملایم
        pulse = 0.85 + 0.15 * math.sin(self._t * 4.0)
        for rr in range(aura_r, 0, -2):
            a = int(50 * (1 - rr / aura_r) ** 1.4 * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(aura, (80, 255, 140, a), (aura_r, aura_r), rr)
        surface.blit(
            aura, (cx - aura_r, cy - aura_r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    def _draw_energy_lines(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        bright: tuple[int, int, int],
    ) -> None:
        """خطوط انرژی از مرکز به سمت رأس‌های ستاره."""
        rot_rad = math.radians(self._rotation)
        num_points = 6
        for i in range(num_points):
            a = rot_rad + (i / num_points) * math.tau
            x1 = cx + math.cos(a) * r * 0.30
            y1 = cy + math.sin(a) * r * 0.30
            x2 = cx + math.cos(a) * r * 0.85
            y2 = cy + math.sin(a) * r * 0.85
            # پالس شفافیت
            alpha_factor = 0.5 + 0.5 * math.sin(self._t * 6.0 + i)
            a_val = int(120 + 100 * alpha_factor)
            line_surf = pygame.Surface((abs(int(x2 - x1)) + 4, abs(int(y2 - y1)) + 4),
                                        pygame.SRCALPHA)
            ox = min(x1, x2) - 2
            oy = min(y1, y2) - 2
            pygame.draw.line(
                line_surf, (*bright, a_val),
                (x1 - ox, y1 - oy),
                (x2 - ox, y2 - oy),
                1,
            )
            surface.blit(line_surf, (ox, oy))

    def _draw_core(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هسته‌ی درخشان در مرکز."""
        pulse = 0.7 + 0.3 * math.sin(self._t * 8.0)
        core_r = max(3, int(r * 0.22 * pulse))

        # هاله‌ی هسته
        glow_size = int(r * 0.5)
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -1):
            a = int(160 * (1 - rr / glow_size) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (200, 255, 220, a), (glow_size, glow_size), rr)
        surface.blit(
            glow, (cx - glow_size, cy - glow_size),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # هسته
        pygame.draw.circle(surface, (220, 255, 230), (cx, cy), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, cy), max(1, core_r // 2))

    def _draw_vertex_glows(
        self,
        surface: pygame.Surface,
        outer_pts: list[tuple[float, float]],
        r: int,
    ) -> None:
        """نقاط درخشان روی رأس‌های ستاره."""
        size = max(2, int(r * 0.13))
        for (vx, vy) in outer_pts:
            # هاله
            glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            for rr in range(size * 2, 0, -1):
                a = int(120 * (1 - rr / (size * 2)))
                if a <= 0:
                    continue
                pygame.draw.circle(glow, (200, 255, 220, a),
                                   (size * 2, size * 2), rr)
            surface.blit(
                glow,
                (int(vx) - size * 2, int(vy) - size * 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )
            # نقطه‌ی مرکزی
            pygame.draw.circle(surface, (255, 255, 255), (int(vx), int(vy)), size)

    def _draw_trail(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """دنباله‌ی ذرات ضعیف پشت کریستال."""
        # ۳ ذره‌ی کوچک با مکان‌های تصادفی (شبه)
        for i in range(3):
            # offset با چرخش زمان
            phase = self._t * 2.0 + i * 2.1
            offset_x = math.cos(phase) * r * 0.7
            offset_y = -r * (0.9 + i * 0.15)
            px = int(cx + offset_x)
            py = int(cy + offset_y)

            size = max(1, int(r * 0.10 - i * 0.5))
            if size <= 0:
                continue

            alpha = int(80 - i * 20)
            if alpha <= 0:
                continue

            dot = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            pygame.draw.circle(dot, (180, 255, 200, alpha),
                               (size * 2, size * 2), size)
            surface.blit(
                dot, (px - size * 2, py - size * 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    def _apply_fade(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        alpha: int,
    ) -> None:
        """پوشش نیمه‌شفاف برای انیمیشن ورود."""
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


# ═══════════════════════════════════════════════════════════════════════════
#  import لازم برای random
# ═══════════════════════════════════════════════════════════════════════════


__all__ = ["SpiralEnemy"]
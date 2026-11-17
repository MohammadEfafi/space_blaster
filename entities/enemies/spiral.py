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

    # مقادیر پایه و ویژگی‌های حرکتی از تنظیمات مرکزی دشمنان دریافت می‌شوند.
    # Base attributes and movement parameters are loaded from the central enemy configuration.
    HP          = S.EnemyCfg.Spiral.HP
    RADIUS      = S.EnemyCfg.Spiral.RADIUS
    SPEED       = S.EnemyCfg.Spiral.SPEED
    SCORE       = S.EnemyCfg.Spiral.SCORE
    DROP_CHANCE = S.EnemyCfg.Spiral.DROP_CHANCE
    AMPLITUDE   = S.EnemyCfg.Spiral.AMPLITUDE
    FREQUENCY   = S.EnemyCfg.Spiral.FREQUENCY
    BODY_COLOR  = S.Palette.ENEMY_SPIRAL

    def _configure(self) -> None:
        # فاز اولیه‌ی تصادفی باعث می‌شود دشمنان هم‌زمان در یک الگوی حرکتی یکسان حرکت نکنند.
        # A random initial phase prevents enemies from following the same movement pattern in sync.
        self._phase = random.uniform(0, math.tau)

    def update_ai(self, dt: float) -> None:
        # حرکت عمودی با سرعت وابسته به زمان سپری‌شده از فریم.
        # Vertical movement scaled by the elapsed frame time.
        self.y += self.SPEED * dt

        # موقعیت افقی با تابع سینوس و با استفاده از فاز اولیه، دامنه و فرکانس محاسبه می‌شود.
        # Horizontal position is calculated using a sine wave, initial phase, amplitude, and frequency.
        self.x = self._base_x + math.sin(self._t * self.FREQUENCY + self._phase) * self.AMPLITUDE

        # زاویه با گذشت زمان افزایش می‌یابد و چرخش پیوسته‌ی دشمن را ایجاد می‌کند.
        # The angle increases over time, producing continuous enemy rotation.
        self.angle = self._t * 180.0



    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        # شعاع ترسیم کمی بزرگ‌تر از شعاع برخورد انتخاب می‌شود تا جزئیات ظاهری فضای کافی داشته باشند.
        # The drawing radius is slightly larger than the collision radius to provide room for visual details.
        r = max(10, int(self.radius * 1.25))
        cx, cy = int(self.x), int(self.y)

        # رنگ پایه و نسخه‌های تیره و روشن آن برای ایجاد عمق و تفکیک اجزای بدنه آماده می‌شوند.
        # The base color and its darker and lighter variants are prepared to add depth and distinguish body details.
        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 80)
        darker = self._darker(base, 130)
        bright = self._lighter(base, 70)

        # ---- ۱. دُم‌های موج‌دار (پشت) ----
        # ---- 1. Wavy tails (rear) ----
        self._draw_tails(surface, cx, cy, r, base, dark)

        # ---- ۲. بدنه‌ی شبح ----
        # ---- 2. Ghost body ----
        self._draw_body_shape(surface, cx, cy, r, base, dark, bright)

        # ---- ۳. دو چشم شیطانی ----
        # ---- 3. Two sinister eyes ----
        self._draw_eyes(surface, cx, cy, r)

        # ---- ۴. خطوط اتریک ----
        # ---- 4. Ethereal lines ----
        self._draw_ethereal_lines(surface, cx, cy, r, darker)

        # ---- ۵. فید ----
        # ---- 5. Fade effect ----
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
        # سه دُم با جهت‌های افقی متفاوت ترسیم می‌شوند تا انتهای بدن حالت چندشاخه پیدا کند.
        # Three tails are drawn at different horizontal offsets to create a branching lower silhouette.
        for i, sign in enumerate((-1, 0, 1)):
            # موج سینوسی دُم
            # Sinusoidal tail movement
            wave = math.sin(self._t * 4.0 + i * 1.5) * r * 0.15

            # نقاط دُم
            # Tail coordinates
            tail_x = cx + sign * int(r * 0.4) + int(wave)
            tail_y = cy - int(r * 1.2)
            tail_len = int(r * 1.0) + i * 4

            # هاله‌ی سبز
            # Green glow
            # چند دایره با شعاع و شفافیت متفاوت، هاله‌ای افزایشی در اطراف محل اتصال دُم ایجاد می‌کنند.
            # Circles with varying radii and transparency create an additive glow around the tail attachment point.
            for rr in range(8, 0, -2):
                a = int(80 * (1 - rr / 8))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*base, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (tail_x - rr * 2, tail_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

            # خود دُم
            # Tail shape
            # دو چندضلعی روی هم، لایه‌ی سایه و سطح اصلی دُم را تشکیل می‌دهند.
            # Two overlapping polygons form the tail's shadow layer and main surface.
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
        # چندضلعی اصلی، فرم پهن سر و لبه‌های نامنظم و چین‌خورده‌ی پایین بدن را مشخص می‌کند.
        # The main polygon defines the broad head and the irregular, folded lower edges of the body.
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
        # Shadow
        # انتقال مختصر نقاط چندضلعی به پایین، سایه‌ای زیر بدنه ایجاد می‌کند.
        # Slightly shifting the polygon points downward creates a shadow beneath the body.
        shadow = [(x, y + 2) for (x, y) in hull]
        pygame.draw.polygon(surface, dark, shadow)

        # بدنه
        # Body
        # ابتدا سطح اصلی پر می‌شود و سپس با یک خط دور روشن، مرز بدنه مشخص‌تر می‌شود.
        # The main surface is filled first, then a bright outline makes the body boundaries more distinct.
        pygame.draw.polygon(surface, base, hull)
        pygame.draw.polygon(surface, bright, hull, 2)

        # درخشش داخلی
        # Inner glow
        # چندضلعی کوچک‌تر داخل بدنه با رنگ روشن‌تر، جلوه‌ی نورانی و عمق بصری ایجاد می‌کند.
        # A smaller polygon with a lighter color creates an illuminated effect and visual depth inside the body.
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
        # موقعیت و اندازه‌ی چشم‌ها نسبت به شعاع بدنه تعیین می‌شود تا با اندازه‌ی دشمن مقیاس شوند.
        # Eye positions and dimensions are derived from the body radius so they scale with the enemy.
        eye_y = cy - int(r * 0.25)
        eye_offset = int(r * 0.28)
        eye_r = max(2, int(r * 0.14))

        # چشم‌ها در دو سمت محور مرکزی و با ساختار بصری یکسان ترسیم می‌شوند.
        # Both eyes are drawn symmetrically on either side of the center axis using the same visual structure.
        for sign in (-1, 1):
            ex = cx + sign * eye_offset

            # هاله
            # Glow
            # سطح شفاف جداگانه امکان ساخت گرادیان قرمز و ترکیب افزایشی آن با تصویر اصلی را فراهم می‌کند.
            # A separate transparent surface allows a red gradient to be created and additively blended with the main image.
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
            # Eye itself (vertical ellipse)
            # بیضی قرمز شکل اصلی چشم را می‌سازد و بیضی روشن‌تر، جزئیات درخشان داخل آن است.
            # The red ellipse forms the main eye, while the lighter ellipse adds a bright inner detail.
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
        # سه خط افقی با فاصله‌ی عمودی ثابت، جزئیات داخلی بدنه را تشکیل می‌دهند.
        # Three horizontal lines with fixed vertical spacing form the body's internal details.
        for i in range(3):
            # عرض خطوط در هر ردیف کاهش می‌یابد تا با فرم بدنه هماهنگ بماند.
            # Line width decreases on each row to follow the body's shape.
            y = cy - int(r * 0.3) + i * int(r * 0.25)
            w = int(r * 0.35) - i * 3
            pygame.draw.line(
                surface, darker,
                (cx - w, y), (cx + w, y), 1,
            )



__all__ = ["SpiralEnemy"]
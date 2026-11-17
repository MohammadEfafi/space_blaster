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
    # ضریب افزایش مدت پاورآپ‌ها برای این سفینه در یک مقدار مشترک نگهداری می‌شود.
    # The power-up duration multiplier for this ship is defined in a single shared value.
    POWERUP_MULTIPLIER: float = 1.5


    def grant_rapid_fire(self, duration: float) -> None:
        # مدت شلیک سریع پیش از واگذاری به پیاده‌سازی کلاس پایه، در ضریب اختصاصی سفینه ضرب می‌شود.
        # The rapid-fire duration is multiplied by the ship-specific factor before being passed to the base implementation.
        super().grant_rapid_fire(duration * self.POWERUP_MULTIPLIER)

    def _get_shot_angles(self) -> list[float]:
        """
        Phantom از ابتدا شلیک سه‌گانه داره (بدون نیاز به پاورآپ).
        با پاورآپ، پنج‌گانه می‌شه.
        """
        # هنگام فعال بودن پاورآپ، پنج زاویه‌ی شلیک برای پوشش گسترده‌تر انتخاب می‌شوند.
        # While a power-up is active, five firing angles are selected for wider coverage.
        if self.powerup_time > 0.0:
            # پنج‌گانه
            return [-110.0, -100.0, -90.0, -80.0, -70.0]
        # سه‌گانه (پیش‌فرض)
        # در حالت عادی، سه زاویه‌ی شلیک الگوی پیش‌فرض سفینه را تشکیل می‌دهند.
        # Under normal conditions, three firing angles form the ship's default firing pattern.
        return [-102.0, -90.0, -78.0]



    def grant_powerup(self, duration=None) -> None:
        """Phantom پاورآپ‌ها رو ۲ برابر دریافت می‌کنه."""
        # در صورت مشخص نبودن مدت، زمان پیش‌فرض تنظیمات استفاده می‌شود.
        # If no duration is provided, the default duration from the game settings is used.
        d = S.PowerupCfg.DURATION if duration is None else duration
        # مدت پاورآپ با ضریب اختصاصی Phantom محاسبه و در وضعیت سفینه ذخیره می‌شود.
        # The power-up duration is multiplied by Phantom's specific factor and stored in the ship state.
        self.powerup_time = d * self.POWERUP_MULTIPLIER



    def get_engine_offsets(self) -> list[tuple[float, float, float]]:
        # سه خروجی موتور در آرایشی متقارن قرار گرفته‌اند و موتور مرکزی مقیاس بزرگ‌تری دارد.
        # Three engine exhaust points are arranged symmetrically, with a larger scale for the center engine.
        return [
            (-0.35, 1.00, 0.60),
            ( 0.00, 1.10, 0.95),
            ( 0.35, 1.00, 0.60),
        ]



    def draw_ship(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # اندازه‌ی سفینه و رنگ‌های مورد استفاده در اجزای مختلف آن آماده می‌شوند.
        # The ship size and the colors used by its different components are prepared.
        r = int(self.radius)
        primary = self.PRIMARY_COLOR
        secondary = self.SECONDARY_COLOR
        highlight = self.HIGHLIGHT_COLOR
        accent = self.ACCENT_COLOR

        # ---- ۲. سایه‌ی زیر (عمق) ----
        # چندضلعی سایه، امتداد کلی بدنه را دنبال می‌کند و جلوه‌ی عمق زیر سفینه را ایجاد می‌کند.
        # The shadow polygon follows the overall hull shape and creates a sense of depth beneath the ship.
        shadow = [
            (cx,                  cy - int(r * 1.20) + 2),
            (cx - int(r * 0.95),  cy + int(r * 0.30) + 2),
            (cx,                  cy + int(r * 0.85) + 2),
            (cx + int(r * 0.95),  cy + int(r * 0.30) + 2),
        ]
        pygame.draw.polygon(surface, (30, 10, 50), shadow)

        # ---- ۳. بال‌های مورب (الماسی) ----
        # بال چپ
        # مختصات بال چپ تعریف می‌شوند و شکل بال راست با قرینه‌سازی افقی آن ساخته می‌شود.
        # The left wing coordinates are defined, and the right wing is created by mirroring them horizontally.
        left_wing = [
            (cx - int(r * 0.40), cy - int(r * 0.50)),   # بالا-داخلی
            (cx - int(r * 1.15), cy - int(r * 0.05)),   # نوک چپ (الماسی)
            (cx - int(r * 1.00), cy + int(r * 0.55)),   # پایین-چپ
            (cx - int(r * 0.30), cy + int(r * 0.35)),   # پایین-داخلی
        ]
        right_wing = [(cx + (cx - x), y) for (x, y) in left_wing]

        # هر دو بال با رنگ ثانویه پر می‌شوند و حاشیه‌ی آن‌ها با رنگ اصلی مشخص می‌شود.
        # Both wings are filled with the secondary color and outlined with the primary color.
        pygame.draw.polygon(surface, secondary, left_wing)
        pygame.draw.polygon(surface, secondary, right_wing)
        pygame.draw.polygon(surface, primary, left_wing, 2)
        pygame.draw.polygon(surface, primary, right_wing, 2)

        # ---- ۴. حلقه‌ی چرخان دور بال‌ها (افکت جادویی) ----
        # نقاط نورانی متحرک در اطراف سفینه، جلوه‌ی حلقه‌ی جادویی چرخان را ایجاد می‌کنند.
        # Animated glowing dots around the ship create the rotating magical ring effect.
        self._draw_rotating_wing_dots(surface, cx, cy, r)

        # ---- ۵. بدنه‌ی اصلی — الماس کشیده ----
        # نقاط چندضلعی، فرم کشیده و الماسی بدنه را از نمای بالا مشخص می‌کنند.
        # The polygon points define the elongated diamond-shaped hull from a top-down view.
        hull = [
            (cx,                  cy - int(r * 1.20)),   # نوک بالا
            (cx - int(r * 0.55),  cy - int(r * 0.20)),   # چپ
            (cx - int(r * 0.45),  cy + int(r * 0.60)),   # پایین-چپ
            (cx,                  cy + int(r * 0.85)),   # دنباله
            (cx + int(r * 0.45),  cy + int(r * 0.60)),
            (cx + int(r * 0.55),  cy - int(r * 0.20)),
        ]
        # بدنه با رنگ اصلی پر می‌شود و سپس حاشیه‌ی روشن آن ترسیم می‌شود.
        # The hull is filled with the primary color and then outlined with a lighter color.
        pygame.draw.polygon(surface, primary, hull)
        pygame.draw.polygon(surface, highlight, hull, 2)

        # ---- ۶. لایه‌ی داخلی (بدنه‌ی روشن‌تر) ----
        # چندضلعی داخلی، سطحی روشن‌تر و کوچک‌تر روی بدنه ایجاد می‌کند.
        # The inner polygon creates a smaller, brighter layer on the hull.
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
        # خطوط با استفاده از علامت متغیر، به‌صورت قرینه در دو طرف بدنه رسم می‌شوند.
        # The lines are drawn symmetrically on both sides of the hull using the changing sign.
        for sign in (-1, 1):
            pygame.draw.line(
                surface, accent,
                (cx + sign * int(r * 0.45), cy - int(r * 0.30)),
                (cx + sign * int(r * 0.20), cy + int(r * 0.55)),
                1,
            )

        # ---- ۸. هسته‌ی درخشان پالسی (قلب شبح) ----
        # هسته‌ی مرکزی با تغییر اندازه و شدت نور، جلوه‌ی ضربان‌دار ایجاد می‌کند.
        # The central core creates a pulsing effect by changing its size and light intensity.
        self._draw_pulsing_core(surface, cx, cy, r)

        # ---- ۹. کابین (نقاب شبح) ----
        # جزئیات کابین به‌صورت نقاب شبح و با دو چشم درخشان رسم می‌شوند.
        # The cockpit details are rendered as a phantom mask with two glowing eyes.
        self._draw_phantom_face(surface, cx, cy, r)

        # ---- ۱۰. رأس‌های درخشان الماسی ----
        # سه رأس اصلی بدنه و بال‌ها برای ایجاد نقاط نورانی انتخاب می‌شوند.
        # The three main vertices of the hull and wings are selected for glowing highlights.
        for (vx, vy) in [(cx, cy - int(r * 1.20)),
                         (cx - int(r * 0.55), cy - int(r * 0.20)),
                         (cx + int(r * 0.55), cy - int(r * 0.20))]:
            self._draw_vertex_glow(surface, vx, vy, int(r * 0.10), accent)



    def _draw_magic_aura(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هاله‌ی بنفش پالسی دور بدنه."""
        # شعاع هاله متناسب با اندازه‌ی سفینه تعیین می‌شود و شدت آن با زمان تغییر می‌کند.
        # The aura radius scales with the ship size, while its intensity varies over time.
        aura_r = int(r * 1.5)
        pulse = 0.85 + 0.15 * math.sin(self._t * 3.0)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)

        # دایره‌های هم‌مرکز با شفافیت تدریجی، هاله‌ای نرم و پخش‌شونده می‌سازند.
        # Concentric circles with gradually changing transparency create a soft, diffused aura.
        for rr in range(aura_r, 0, -3):
            a = int(35 * (1 - rr / aura_r) ** 1.5 * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(aura, (190, 90, 255, a), (aura_r, aura_r), rr)

        # هاله با ترکیب افزایشی روی سطح اصلی قرار می‌گیرد تا درخشش بنفش ایجاد شود.
        # The aura is additively blended onto the main surface to create a purple glow.
        surface.blit(
            aura, (cx - aura_r, cy - aura_r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

    def _draw_rotating_wing_dots(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """نقاط درخشان چرخان روی لبه‌ی بال‌ها."""
        # تعداد نقاط و شعاع مسیر حرکت آن‌ها، محدوده‌ی حلقه‌ی نورانی را مشخص می‌کنند.
        # The number of dots and their orbit radius define the glowing ring's path.
        num = 6
        radius = r * 1.05

        # زاویه‌ی هر نقطه با زمان تغییر می‌کند و ضریب عمودی، مسیر حرکت را بیضوی می‌سازد.
        # Each dot's angle changes over time, while the vertical scale creates an elliptical orbit.
        for i in range(num):
            angle = (i / num) * math.tau + self._t * 1.5
            px = cx + int(math.cos(angle) * radius)
            py = cy + int(math.sin(angle) * radius * 0.7)
            size = 2

            # شفافیت هر نقطه با اختلاف فاز تغییر می‌کند تا درخشش آن‌ها یکسان نباشد.
            # Each dot's transparency changes with a phase offset so their brightness varies independently.
            a = 0.5 + 0.5 * math.sin(self._t * 4.0 + i * 0.8)
            alpha = int(100 + 120 * a)
            dot = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
            pygame.draw.circle(dot, (255, 150, 255, alpha),
                               (size * 2, size * 2), size * 2)

            # نقطه‌ی نورانی با ترکیب افزایشی روی سطح اصلی قرار می‌گیرد.
            # The glowing dot is additively blended onto the main surface.
            surface.blit(
                dot, (px - size * 2, py - size * 2),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    def _draw_pulsing_core(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هسته‌ی درخشان مرکزی با پالس."""
        # تابع سینوسی، اندازه‌ی هسته را در طول زمان به‌صورت ضربانی تغییر می‌دهد.
        # The sine function changes the core size rhythmically over time.
        pulse = 0.7 + 0.3 * math.sin(self._t * 5.0)
        core_r = max(3, int(r * 0.22 * pulse))
        core_y = cy - int(r * 0.10)

        # هاله
        # هاله با دایره‌های هم‌مرکز و شفافیت وابسته به پالس ساخته می‌شود.
        # The glow is built from concentric circles whose transparency depends on the pulse.
        glow_size = int(r * 0.5)
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -1):
            a = int(160 * (1 - rr / glow_size) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (255, 180, 255, a),
                               (glow_size, glow_size), rr)

        # هاله در مرکز بدنه با ترکیب افزایشی رسم می‌شود.
        # The glow is additively blended at the center of the hull.
        surface.blit(
            glow, (cx - glow_size, core_y - glow_size),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # هسته
        # دو دایره‌ی تو‌در‌تو، سطح روشن هسته و مرکز سفید آن را تشکیل می‌دهند.
        # Two nested circles form the bright core surface and its white center.
        pygame.draw.circle(surface, (255, 220, 255), (cx, core_y), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, core_y), max(1, core_r // 2))

    def _draw_phantom_face(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """نقاب شبح: دو چشم درخشان."""
        # موقعیت عمودی نقاب، فاصله‌ی دو چشم و شعاع آن‌ها متناسب با اندازه‌ی سفینه محاسبه می‌شوند.
        # The mask's vertical position, eye spacing, and eye radius are calculated relative to the ship size.
        face_y = cy - int(r * 0.15)
        eye_y = face_y
        eye_offset = int(r * 0.18)
        eye_r = max(2, int(r * 0.09))

        # دو چشم درخشان صورتی
        # حلقه‌ی تکرار، چشم چپ و راست را با فاصله‌ی متقارن از مرکز رسم می‌کند.
        # The loop draws the left and right eyes at symmetrical offsets from the center.
        for sign in (-1, 1):
            ex = cx + sign * eye_offset

            # هاله‌ی چشم
            # دایره‌های هم‌مرکز با شفافیت متغیر، هاله‌ی نور اطراف هر چشم را می‌سازند.
            # Concentric circles with varying transparency create the glow around each eye.
            glow = pygame.Surface((eye_r * 6, eye_r * 6), pygame.SRCALPHA)
            for rr in range(eye_r * 3, 0, -1):
                a = int(100 * (1 - rr / (eye_r * 3)))
                if a <= 0:
                    continue
                pygame.draw.circle(glow, (255, 150, 255, a),
                                   (eye_r * 3, eye_r * 3), rr)

            # هاله در موقعیت چشم با ترکیب افزایشی روی سطح اصلی قرار می‌گیرد.
            # The glow is additively blended onto the main surface at the eye position.
            surface.blit(
                glow, (ex - eye_r * 3, eye_y - eye_r * 3),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

            # خود چشم
            # دو دایره‌ی هم‌مرکز، سطح روشن چشم و بخش داخلی صورتی آن را تشکیل می‌دهند.
            # Two concentric circles form the bright eye surface and its pink inner region.
            pygame.draw.circle(surface, (255, 220, 255), (ex, eye_y), eye_r)
            pygame.draw.circle(surface, (255, 80, 200), (ex, eye_y), max(1, eye_r - 1))

    def _draw_vertex_glow(
        self,
        surface: pygame.Surface,
        x: int, y: int, size: int,
        color: tuple[int, int, int],
    ) -> None:
        """نقطه‌ی درخشان روی رأس بدنه."""
        # اندازه‌ی هاله حداقل روی دو پیکسل تنظیم می‌شود تا جلوه‌ی نور قابل مشاهده بماند.
        # The glow size is clamped to at least two pixels to keep the light effect visible.
        size = max(2, size)

        # سطحی شفاف برای ساخت هاله ایجاد می‌شود تا پس‌زمینه‌ی اطراف تغییر نکند.
        # A transparent surface is created for the glow so the surrounding background remains unaffected.
        glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)

        # دایره‌های هم‌مرکز با شعاع و شفافیت متغیر، هاله‌ای تدریجی و نرم می‌سازند.
        # Concentric circles with varying radii and transparency create a smooth, gradual glow.
        for rr in range(size * 2, 0, -1):
            a = int(120 * (1 - rr / (size * 2)))
            if a <= 0:
                continue
            pygame.draw.circle(glow, (*color, a), (size * 2, size * 2), rr)

        # هاله با ترکیب افزایشی روی سطح اصلی قرار می‌گیرد تا جلوه‌ی درخشش ایجاد شود.
        # The glow is additively blended onto the main surface to create a luminous effect.
        surface.blit(
            glow, (x - size * 2, y - size * 2),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # نقطه‌ی سفید مرکزی، روشن‌ترین بخش جلوه‌ی نورانی رأس را تشکیل می‌دهد.
        # The central white dot forms the brightest part of the vertex glow.
        pygame.draw.circle(surface, (255, 255, 255), (x, y), max(1, size // 2))


__all__ = ["Phantom"]
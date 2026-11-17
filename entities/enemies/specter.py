"""

entities/enemies/specter.py
==========================

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
        # زمان‌سنج فاز، وضعیت دیده‌شدن و میزان شفافیت اولیه‌ی شبح را تنظیم می‌کند.
        # Initializes the phase timer, visibility state, and initial ghost opacity.
        self._phase_timer = 0.0
        self._visible = True
        self._alpha = 1.0
        # ذرات orbit
        # چهار زاویه‌ی ثابت برای قرارگیری ذرات چرخان اطراف شبح تعیین می‌شوند.
        # Defines four fixed angles for positioning particles orbiting the ghost.
        self._orbits = [i * math.tau / 4 for i in range(4)]

    def update_ai(self, dt: float) -> None:
        # حرکت عمودی شبح و زمان سپری‌شده در فاز فعلی را به‌روزرسانی می‌کند.
        # Updates the ghost's vertical movement and elapsed time in the current phase.
        self.y += self.SPEED * dt
        self._phase_timer += dt

        # در فاز قابل‌مشاهده، پس از پایان زمان تعیین‌شده وارد حالت نامرئی می‌شود.
        # Switches to the invisible state when the visible phase duration expires.
        if self._visible:
            if self._phase_timer >= self.VISIBLE_DURATION:
                self._phase_timer = 0.0
                self._visible = False
            # شفافیت هنگام حضور شبح به‌تدریج به مقدار کامل افزایش می‌یابد.
            # Gradually restores full opacity while the ghost is visible.
            self._alpha = min(1.0, self._alpha + dt * 4.0)
        else:
            # پس از پایان فاز نامرئی، شبح دوباره وارد حالت قابل‌مشاهده می‌شود.
            # Returns the ghost to the visible state when the invisible phase expires.
            if self._phase_timer >= self.INVISIBLE_DURATION:
                self._phase_timer = 0.0
                self._visible = True
            # هنگام نامرئی‌شدن، شفافیت کاهش می‌یابد اما از حداقل مقدار تعیین‌شده کمتر نمی‌شود.
            # Reduces opacity while invisible without going below the configured minimum.
            self._alpha = max(0.05, self._alpha - dt * 4.0)

    def take_damage(self, damage: int) -> bool:
        # در حالت نامرئی، آسیب دریافتی نادیده گرفته می‌شود.
        # Ignores incoming damage while the ghost is invisible.
        if not self._visible:
            return False
        return super().take_damage(damage)

    def _do_shoot(self) -> list:
        # شبح فقط در فاز قابل‌مشاهده اجازه‌ی شلیک دارد.
        # Allows the ghost to shoot only during its visible phase.
        if not self._visible:
            return []
        return super()._do_shoot()



    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        # شعاع نمایشی و مرکز بدنه را برای رسم اجزای مختلف محاسبه می‌کند.
        # Calculates the visual radius and body center for drawing its components.
        r = int(self.radius * 1.3)
        cx, cy = int(self.x), int(self.y)

        # رنگ‌های اصلی و مکمل برای لایه‌های بدنه، سایه و درخشش تعیین می‌شوند.
        # Defines the primary and complementary colors for the body, shadows, and highlights.
        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 110)
        bright = self._lighter(base, 90)
        white = (255, 240, 255)

        # شفافیت نهایی از ترکیب شفافیت داخلی شبح و مقدار دریافتی از سیستم رسم به دست می‌آید.
        # Combines the ghost's internal opacity with the alpha value supplied by the rendering system.
        a = int(self._alpha * alpha)
        if a <= 8:
            # فقط هاله‌ی خیلی کم برای این‌که کاربر بدونه کجاست
            # در شفافیت بسیار پایین، تنها یک هاله‌ی ضعیف برای مشخص‌کردن موقعیت شبح رسم می‌شود.
            # At very low opacity, draws only a faint glow to indicate the ghost's position.
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
        # هاله‌ی بیرونی با حلقه‌های شفاف ساخته می‌شود و شدت آن متناسب با شفافیت شبح است.
        # Builds the outer aura from translucent rings, scaled by the ghost's opacity.
        aura_r = int(r * 2.2)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -4):
            aa = int(70 * (1 - rr / aura_r) ** 2 * alpha_frac)
            if aa > 0:
                pygame.draw.circle(aura, (*base, aa), (aura_r, aura_r), rr)
        # لایه‌ی سفید-نزدیک مرکز
        # لایه‌ی داخلی با رنگ روشن‌تر، مرکز هاله را برجسته می‌کند.
        # Adds a brighter inner layer to emphasize the center of the aura.
        for rr in range(int(aura_r * 0.5), 0, -2):
            aa = int(60 * (1 - rr / (aura_r * 0.5)) * alpha_frac)
            if aa > 0:
                pygame.draw.circle(aura, (255, 240, 255, aa), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۲. دُم‌های موج‌دار (۵ تا، بلند، زیگزاگ) ----
        # پنج دُم با موقعیت‌های افقی متفاوت، ساختار کشیده و شناور شبح را تشکیل می‌دهند.
        # Five tails at different horizontal offsets create the ghost's elongated, floating shape.
        for i in range(5):
            t = (i - 2) / 2.0
            phase = self._t * 4 + i * 1.1
            wave_x = math.sin(phase) * 14
            tx = cx + int(t * r * 0.7) + int(wave_x)
            ty = cy + int(r * 0.35)
            tail_len = int(r * (1.0 + abs(t) * 0.4))

            # نقاط زیگزاگ
            # نقاط مسیر هر دُم با نوسان سینوسی محاسبه می‌شوند تا حرکت موج‌دار ایجاد شود.
            # Calculates each tail's zigzag points with a sine wave to create flowing motion.
            pts = [(tx, ty)]
            segs = 4
            for j in range(1, segs + 1):
                tj = j / segs
                px = tx + int(math.sin(phase + j * 1.3) * r * 0.15 * tj)
                py = ty + int(tail_len * tj)
                pts.append((px, py))

            # هاله‌ی دُم
            # هاله‌ی درخشان در بخش میانی دُم قرار می‌گیرد و با شفافیت کلی شبح هماهنگ است.
            # Places a glowing aura around the middle of the tail, scaled by the ghost's opacity.
            for rr in range(int(r * 0.25), 0, -2):
                aa = int(100 * (1 - rr / (r * 0.25)) * alpha_frac)
                if aa > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (*bright, aa), (rr * 2, rr * 2), rr)
                    surface.blit(g, (tx - rr * 2, ty + tail_len // 2 - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

            # خط زیگزاگ
            # قطعات مسیر از بالا به پایین رسم می‌شوند و ضخامت و شفافیت آن‌ها کاهش می‌یابد.
            # Draws the tail segments from top to bottom with progressively reduced width and opacity.
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
        # چهار ذره در مسیرهای بیضی‌شکل اطراف مرکز شبح گردش می‌کنند.
        # Four particles orbit the ghost's center along elliptical paths.
        orbit_r = r * 1.1
        for i in range(4):
            angle = self._orbits[i] + self._t * 1.5
            px = cx + int(math.cos(angle) * orbit_r)
            py = cy + int(math.sin(angle) * orbit_r * 0.7)
            size = 2
            # برای هر ذره یک سطح مستقل ساخته می‌شود تا هاله‌ی نور آن جداگانه ترکیب شود.
            # Creates a separate surface for each particle so its glow can be blended independently.
            g = pygame.Surface((size * 8, size * 8), pygame.SRCALPHA)
            for rr in range(size * 4, 0, -1):
                aa = int(180 * (1 - rr / (size * 4)) * alpha_frac)
                if aa > 0:
                    pygame.draw.circle(g, (*white, aa), (size * 4, size * 4), rr)
            surface.blit(g, (px - size * 4, py - size * 4),
                         special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۴. بدنه‌ی شبح‌وار (سه‌لایه) ----
        # چرخش لایه‌های هندسی بدنه با گذشت زمان تغییر می‌کند.
        # Animates the rotation of the ghost's geometric body layers over time.
        rot = self._t * 1.2

        # لایه‌ی بیرونی (چادر)
        # نقاط پیرامونی با نوسان مستقل ساخته می‌شوند تا لبه‌ی بدنه حالت نامنظم و زنده داشته باشد.
        # Generates independently oscillating perimeter points for an irregular, animated outer body.
        outer_pts = []
        for i in range(16):
            angle = rot + i * math.tau / 16
            wobble = 1.0 + 0.18 * math.sin(self._t * 3.5 + i * 0.8)
            outer_pts.append((
                cx + math.cos(angle) * r * wobble,
                cy + math.sin(angle) * r * 0.95 * wobble,
            ))
        # رسم روی سطح شفاف، امکان اعمال جداگانه‌ی شفافیت و خط دور را فراهم می‌کند.
        # Rendering onto a transparent surface allows independent control of fill and outline opacity.
        tmp = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
        local = [(p[0] - cx + r * 2.5, p[1] - cy + r * 2.5) for p in outer_pts]
        pygame.draw.polygon(tmp, (*base, int(160 * alpha_frac)), local)
        pygame.draw.polygon(tmp, (*bright, int(255 * alpha_frac)), local, 2)
        surface.blit(tmp, (cx - r * 2.5, cy - r * 2.5))

        # لایه‌ی میانی
        # لایه‌ی داخلی با شعاع کوچک‌تر و نوسان متفاوت، حجم بصری بدنه را افزایش می‌دهد.
        # Adds visual depth with a smaller inner layer and a different oscillation pattern.
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
        # شدت ضربان هسته در طول زمان تغییر می‌کند و اندازه‌ی آن را تحت تأثیر قرار می‌دهد.
        # Modulates the core's pulse over time, affecting its rendered size.
        pulse = 0.7 + 0.3 * math.sin(self._t * 6)
        core_r = int(r * 0.35 * pulse)

        # حلقه‌های نورانی اطراف هسته، درخششی تدریجی به سمت مرکز ایجاد می‌کنند.
        # Glowing rings around the core create a gradual light transition toward the center.
        for rr in range(int(r * 0.6), 0, -3):
            aa = int(200 * (1 - rr / (r * 0.6)) ** 1.5 * pulse * alpha_frac)
            if aa > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 240, 255, aa), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, cy - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # هسته (سه لایه)
        # سه دایره‌ی هم‌مرکز با اندازه و روشنایی متفاوت، هسته‌ی چندلایه را تشکیل می‌دهند.
        # Three concentric circles with different sizes and brightness levels form the layered core.
        pygame.draw.circle(surface, base, (cx, cy), max(1, int(core_r * alpha_frac)))
        pygame.draw.circle(surface, bright, (cx, cy), max(1, int(core_r * 0.7 * alpha_frac)))
        pygame.draw.circle(surface, white, (cx, cy), max(1, int(core_r * 0.4 * alpha_frac)))

        # ---- ۶. سه چشم شیطانی ----
        # دو چشم جانبی و یک چشم بالایی، در سه موقعیت مشخص روی بدنه قرار می‌گیرند.
        # Places two side eyes and one upper eye at three defined positions on the body.
        eye_positions = [
            (cx - int(r * 0.35), cy - int(r * 0.15)),
            (cx + int(r * 0.35), cy - int(r * 0.15)),
            (cx, cy - int(r * 0.45)),
        ]
        for idx, (ex, ey) in enumerate(eye_positions):
            eye_r = max(3, int(r * 0.10))
            # هاله
            # هاله‌ی سفید اطراف هر چشم با حلقه‌های شفاف و ترکیب افزایشی رسم می‌شود.
            # Draws a white glow around each eye using translucent rings and additive blending.
            for rr in range(eye_r * 4, 0, -1):
                aa = int(180 * (1 - rr / (eye_r * 4)) * alpha_frac)
                if aa > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (*white, aa), (rr * 2, rr * 2), rr)
                    surface.blit(g, (ex - rr * 2, ey - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)
            # سفیدی چشم
            # بخش روشن چشم با شفافیت محاسبه‌شده‌ی شبح رسم می‌شود.
            # Draws the bright eye area using the ghost's calculated opacity.
            pygame.draw.circle(surface, (255, 255, 255, a), (ex, ey), eye_r)
            # مردمک (صورتی)
            # مردمک رنگی در مرکز چشم قرار می‌گیرد و اندازه‌ی آن از شعاع چشم کوچک‌تر است.
            # Places a colored pupil at the center of the eye, smaller than the eye itself.
            pygame.draw.circle(surface, (*base, a), (ex, ey), max(1, eye_r // 2))
            # برق
            # بازتاب کوچک سفید، جلوه‌ی براق چشم را ایجاد می‌کند.
            # Adds a small white reflection to give the eye a glossy appearance.
            pygame.draw.circle(surface, (255, 255, 255, a),
                               (ex - 1, ey - 1), max(1, eye_r // 4))

        # ---- ۷. هشدار ناپدید شدن ----
        # در بخش پایانی فاز قابل‌مشاهده، نشانگرهای چرخان هشدار ناپدیدشدن را نمایش می‌دهند.
        # Displays rotating disappearance warnings during the final part of the visible phase.
        if self._visible and self._phase_timer > self.VISIBLE_DURATION * 0.65:
            # میزان پیشرفت هشدار در بازه‌ی پایانی فاز قابل‌مشاهده محاسبه می‌شود.
            # Calculates warning progress across the final portion of the visible phase.
            progress = (self._phase_timer - self.VISIBLE_DURATION * 0.65) / (self.VISIBLE_DURATION * 0.35)
            warn_r = int(r * (1.2 + progress * 0.8))
            # دایره‌ی نازک
            # نقاط هشدار روی یک مسیر دایره‌ای قرار می‌گیرند و همراه زمان می‌چرخند.
            # Positions warning particles along a circular path and rotates them over time.
            for i in range(int(warn_r * 0.5)):
                angle = (i / (warn_r * 0.5)) * math.tau + self._t * 3
                wx = cx + int(math.cos(angle) * warn_r)
                wy = cy + int(math.sin(angle) * warn_r)
                aa = int(200 * progress * (1 - abs(i / (warn_r * 0.5) - 0.5) * 2) * alpha_frac)
                if aa > 0:
                    pygame.draw.circle(surface, (255, 200, 100, aa), (wx, wy), 2)

        # ---- ۸. نوار HP ----
        if self.hp < self.max_hp:
            # نوار سلامتی بالای شبح قرار می‌گیرد و مقدار آن متناسب با HP باقی‌مانده است.
            # Places the health bar above the ghost and scales its fill with the remaining HP.
            w = int(r * 2)
            h = 3
            x = cx - w // 2
            y = cy - int(r * 1.4)
            bg = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            surface.blit(bg, (x - 1, y - 1))
            ratio = max(0.0, self.hp / self.max_hp)
            pygame.draw.rect(surface, (255, 80, 255), (x, y, int(w * ratio), h))


__all__ = ["SpecterEnemy"]
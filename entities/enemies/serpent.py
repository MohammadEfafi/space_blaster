"""

entities/enemies/sentinel.py
==========================

SERPENT — مار فضایی (نسخه‌ی نهایی v3).

ظاهر:
    • بدنه‌ی بلند با ۳۰ نقطه (دایره‌های هم‌پوشان برای بدنه‌ی صاف)
    • سر پلی‌گونی با شکل افعی (پهن در عقب، باریک در دهان)
    • ۲ چشم زرد با مردمک عمودی (شیار)
    • ۲ نیش + زبان چنگالی
    • تیغ روی سر + الماس‌های تزئینی روی بدنه
"""

from __future__ import annotations

import math
import random
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


class SerpentEnemy(Enemy):
    """SERPENT — مار فضایی."""

    KIND = EnemyKind.SERPENT

    HP = 4
    RADIUS = 20
    SPEED = 80
    SCORE = 55
    DROP_CHANCE = 0.25
    SHOOT_CD = 2.0
    BULLET_SPEED = 240
    BODY_COLOR = (120, 255, 100)

    # --- تنظیمات بدنه ---
    NUM_SEGMENTS = 30
    SEGMENT_SPACING = 0.035

    def _configure(self) -> None:
        # فاز اولیه‌ی حرکت موجی را تصادفی تعیین می‌کند تا مسیر مارها یکسان نباشد.
        # Randomizes the initial wave phase so different serpents do not follow identical paths.
        self._phase = random.uniform(0, math.tau)
        self._eye_look = (0.0, 1.0)  # چشم رو به پایین

    def update_ai(self, dt: float) -> None:
        # حرکت عمودی مار را متناسب با زمان سپری‌شده در فریم انجام می‌دهد.
        # Advances the serpent vertically according to the elapsed frame time.
        self.y += self.SPEED * dt
        # حرکت S شکل (دو موج روی هم)
        # ترکیب دو موج سینوسی با فرکانس و دامنه‌ی متفاوت، مسیر مار را شکل می‌دهد.
        # Combines two sine waves with different frequencies and amplitudes to shape the serpent's path.
        wave1 = math.sin(self._t * 3.0 + self._phase) * 45
        wave2 = math.sin(self._t * 5.0 + self._phase * 1.5) * 18
        target_x = self._base_x + wave1 + wave2

        # مار از کادر بیرون نزنه
        # موقعیت افقی مار را در محدوده‌ی مجاز صفحه نگه می‌دارد.
        # Keeps the serpent's horizontal position within the screen boundaries.
        margin = self.radius + 20
        self.x = max(margin, min(S.Window.WIDTH - margin, target_x))

        # چشم‌ها بازیکن رو دنبال می‌کنن
        # جهت نگاه چشم‌ها را به‌تدریج به سمت موقعیت بازیکن تغییر می‌دهد.
        # Gradually adjusts the eye direction toward the player's position.
        player = getattr(self.scene, "player", None) if self.scene else None
        if player and player.alive:
            dx = player.x - self.x
            dy = player.y - self.y
            d = math.hypot(dx, dy) or 1.0
            target = (dx / d, dy / d)
            blend = min(1.0, dt * 5.0)
            self._eye_look = (
                self._eye_look[0] + (target[0] - self._eye_look[0]) * blend,
                self._eye_look[1] + (target[1] - self._eye_look[1]) * blend,
            )

        # ذرات trail
        # با احتمال وابسته به زمان فریم، ذراتی در پشت مار ایجاد می‌کند.
        # Emits particles behind the serpent with a probability scaled by frame time.
        if self.scene is not None and random.random() < dt * 15:
            try:
                from systems.particles import ParticleKind
                self.scene.particles.emit_burst(
                    self.x, self.y + self.radius * 0.5, count=2,
                    color_start=(150, 255, 150), color_end=(50, 200, 50),
                    speed_min=20, speed_max=60,
                    life_min=0.3, life_max=0.6,
                    size_min=2, size_max=4,
                    kind=ParticleKind.SPARK, additive=True,
                )
            except Exception:
                # در صورت بروز خطا در ایجاد ذرات، اجرای هوش مصنوعی دشمن ادامه پیدا می‌کند.
                # Keeps the enemy AI running if particle creation fails.
                pass

    def _do_shoot(self) -> list:
        # بدون صحنه‌ی فعال، امکان ساخت و ثبت گلوله‌ها وجود ندارد.
        # Cannot create or register projectiles without an active scene.
        if self.scene is None:
            return []
        bullets = []
        # سه گلوله با اختلاف زاویه‌ای، یک الگوی پخش محدود ایجاد می‌کنند.
        # Three projectiles with angular offsets create a narrow spread pattern.
        for angle_offset in (-0.25, 0.0, 0.25):
            angle = math.pi / 2 + angle_offset
            try:
                b = Bullet(
                    self.x, self.y + self.radius * 0.5,
                    math.cos(angle) * self.BULLET_SPEED,
                    math.sin(angle) * self.BULLET_SPEED,
                    friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
                )
                bullets.append(b)
            except Exception:
                # خطای ساخت یک گلوله مانع تلاش برای ساخت گلوله‌های دیگر نمی‌شود.
                # A projectile creation failure does not prevent attempts to create the others.
                pass
        try:
            # گلوله‌های ساخته‌شده را به صحنه اضافه می‌کند و صدای شلیک را پخش می‌کند.
            # Adds the created projectiles to the scene and plays the shooting sound.
            for b in bullets:
                self.scene.spawn_bullet(b)
            self.scene.audio.play("enemy_shoot")
        except Exception:
            # خطاهای ثبت گلوله یا پخش صدا را از انتشار به سایر بخش‌ها بازمی‌دارد.
            # Prevents projectile registration or audio errors from propagating to other systems.
            pass
        return bullets


    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        # اندازه‌ی کلی اجزای بدنه را بر اساس شعاع دشمن تعیین می‌کند.
        # Determines the overall size of the body components from the enemy's radius.
        r = int(self.radius * 1.1)

        # رنگ‌های پایه و سایه برای تفکیک لایه‌های مختلف بدنه استفاده می‌شوند.
        # Base and shadow colors distinguish the serpent's different body layers.
        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 110)
        darker = self._darker(base, 170)
        bright = self._lighter(base, 80)
        glow = (200, 255, 180)

        # ---- ۱. محاسبه‌ی موقعیت نقاط ستون فقرات ----
        # موقعیت هر قطعه از بدنه با استفاده از زمان گذشته و فاصله‌ی آن از سر محاسبه می‌شود.
        # Calculates each body segment's position using elapsed time and its distance behind the head.
        spine = []
        margin = self.radius + 20
        for i in range(self.NUM_SEGMENTS):
            t_behind = self._t - i * self.SEGMENT_SPACING
            target_x = self._base_x + math.sin(t_behind * 3.0 + self._phase) * 45 \
                + math.sin(t_behind * 5.0 + self._phase * 1.5) * 18

            # محدود کردن به کادر (دقیقا مثل update_ai)
            # همان محدودیت حرکت افقی در منطق هوش مصنوعی را برای تمام قطعات بدنه اعمال می‌کند.
            # Applies the same horizontal movement boundaries used by the AI to every body segment.
            clamped_x = max(margin, min(S.Window.WIDTH - margin, target_x))

            # فاصله‌ی عمودی قطعات از سر با سرعت حرکت و فاصله‌ی زمانی بین قطعات تعیین می‌شود.
            # Determines each segment's vertical offset using movement speed and segment spacing.
            y = self.y - i * (self.SPEED * self.SEGMENT_SPACING)
            spine.append((clamped_x, y))

        # ---- ۲. رسم بدنه از دم به سر (دایره‌های هم‌پوشان) ----
        # رسم از دم به سر باعث می‌شود قطعات نزدیک‌تر به سر روی قطعات عقبی قرار بگیرند.
        # Drawing from tail to head ensures that segments closer to the head appear above those behind them.
        for i in reversed(range(self.NUM_SEGMENTS)):
            px, py = spine[i]
            t = i / (self.NUM_SEGMENTS - 1)

            # اندازه (سر بزرگ، دم کوچک)
            # شعاع قطعات در امتداد بدن کاهش می‌یابد تا شکل کلی مار از سر به دم باریک شود.
            # Gradually reduces segment size toward the tail to create a tapered body.
            w = r * (0.9 - t * 0.7)
            if t < 0.1:
                w = r * 0.95
            w = max(2, int(w))

            # سایه
            pygame.draw.circle(surface, darker, (int(px) + 2, int(py) + 2), w)

            # بدنه
            pygame.draw.circle(surface, base, (int(px), int(py)), w)

            # خط دور
            pygame.draw.circle(surface, dark, (int(px), int(py)), w, 1)

            # پولک‌های تزئینی (الماس روی هر ۳ نقطه)
            # الگوی الماسی فقط روی برخی قطعات رسم می‌شود تا جزئیات بدنه بیش از حد متراکم نشوند.
            # Draws diamond scales on selected segments to avoid overcrowding the body details.
            if i % 3 == 0 and w > 5:
                size = w * 0.35
                diamond = [
                    (px, py - size),
                    (px + size, py),
                    (px, py + size),
                    (px - size, py),
                ]
                pygame.draw.polygon(surface, darker, diamond, 1)

            # خط شکم روشن (روی مرکز)
            # خط روشن مرکزی، بخش زیرین و ساختار طولی بدن را از سایر قسمت‌ها متمایز می‌کند.
            # The central highlight distinguishes the underside and longitudinal structure of the body.
            if w > 4:
                pygame.draw.line(surface, bright,
                                 (int(px - w * 0.3), int(py)),
                                 (int(px + w * 0.3), int(py)), 1)

        # ---- ۳. سر مار (روی همه) ----
        # سر پس از بدنه رسم می‌شود تا روی تمام قطعات دیگر قرار بگیرد.
        # Draws the head after the body so it appears above all other segments.
        head_x, head_y = spine[0]
        head_w = r * 0.95
        self._draw_snake_head(surface, head_x, head_y, head_w, base, dark, darker, bright, glow)

        # ---- ۴. نوار HP ----
        if self.hp < self.max_hp:
            # نوار سلامتی در کنار سر نمایش داده می‌شود و با کاهش HP کوتاه‌تر می‌شود.
            # Displays the health bar beside the head, shortening as HP decreases.
            w = int(r * 1.2)
            h = 3
            x = int(head_x) + int(head_w * 1.2)
            y = int(head_y) - h // 2
            bg = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 200))
            surface.blit(bg, (x - 1, y - 1))
            ratio = max(0.0, self.hp / self.max_hp)
            pygame.draw.rect(surface, (80, 255, 140), (x, y, int(w * ratio), h))



    def _draw_snake_head(self, surface, hx, hy, hw, base, dark, darker, bright, glow):
        # --- هاله‌ی خیلی کوچک و محو (فقط دور سر، نه کل صفحه) ---
        # هاله‌ی محدود اطراف سر، جلوه‌ی درخشش ایجاد می‌کند بدون اینکه بخش بزرگی از صفحه را بپوشاند.
        # Creates a localized glow around the head without covering a large portion of the screen.
        for rr in range(int(hw * 1.2), 0, -2):
            a = int(30 * (1 - rr / (hw * 1.2)))
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*glow, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (int(hx) - rr * 2, int(hy) - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # ---- پلی‌گون سر (شکل افعی: پهن در عقب، باریک در دهان) ----
        # نقاط چندضلعی، پهنای قسمت عقبی سر و باریک‌شدن آن به سمت دهان را مشخص می‌کنند.
        # The polygon vertices define the broad rear of the head and its narrowing toward the mouth.
        head_pts = [
            (hx - hw * 0.6,  hy - hw * 0.6),   # عقب-چپ
            (hx + hw * 0.6,  hy - hw * 0.6),   # عقب-راست
            (hx + hw * 0.8,  hy + hw * 0.1),   # شانه-راست
            (hx + hw * 0.45, hy + hw * 0.7),   # دهان-راست
            (hx,             hy + hw * 1.0),   # نوک دهان
            (hx - hw * 0.45, hy + hw * 0.7),   # دهان-چپ
            (hx - hw * 0.8,  hy + hw * 0.1),   # شانه-چپ
        ]
        pygame.draw.polygon(surface, darker, [(x + 2, y + 2) for x, y in head_pts])
        pygame.draw.polygon(surface, base, head_pts)
        pygame.draw.polygon(surface, bright, head_pts, 2)

        # ---- تیغ روی سر ----
        # خط مرکزی روشن، تیغ و امتداد طولی بخش بالایی سر را نمایش می‌دهد.
        # The central highlight represents the crest and longitudinal detail along the top of the head.
        pygame.draw.line(surface, bright,
                         (int(hx), int(hy - hw * 0.5)),
                         (int(hx), int(hy + hw * 0.8)), 1)

        # ---- ۲ چشم زرد با شیار عمودی ----
        # اجزای هر دو چشم با قرینه‌سازی نسبت به محور مرکزی سر رسم می‌شوند.
        # Draws both eyes symmetrically around the head's central axis.
        for sign in (-1, 1):
            ex = hx + sign * hw * 0.45
            ey = hy + hw * 0.05
            eye_r = max(4, int(hw * 0.28))

            # هاله‌ی چشم (خیلی کوچک)
            # هاله‌ی کوچک با ترکیب افزایشی، نور قرمز اطراف هر چشم را ایجاد می‌کند.
            # Uses additive blending to create a small red glow around each eye.
            for rr in range(eye_r * 2, 0, -1):
                a = int(120 * (1 - rr / (eye_r * 2)))
                if a > 0:
                    g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                    pygame.draw.circle(g, (255, 80, 80, a), (rr * 2, rr * 2), rr)
                    surface.blit(g, (int(ex) - rr * 2, int(ey) - rr * 2),
                                 special_flags=pygame.BLEND_RGBA_ADD)

            # سفیدی چشم (زرد)
            pygame.draw.circle(surface, (255, 220, 60), (int(ex), int(ey)), eye_r)
            pygame.draw.circle(surface, dark, (int(ex), int(ey)), eye_r, 1)

            # مردمک شیاری (به سمت بازیکن)
            # جابه‌جایی مردمک بر اساس بردار نگاه، جهت توجه مار به بازیکن را نشان می‌دهد.
            # Offsets the slit pupil according to the look vector to show the serpent's focus on the player.
            pupil_x = ex + self._eye_look[0] * eye_r * 0.3
            pupil_y = ey + self._eye_look[1] * eye_r * 0.3
            pw = max(1, eye_r // 3)
            ph = eye_r
            pygame.draw.ellipse(
                surface, (20, 20, 20),
                (int(pupil_x) - pw, int(pupil_y) - ph, pw * 2, ph * 2),
            )

            # برق چشم
            # بازتاب سفید کوچک، ظاهر براق چشم را کامل می‌کند.
            # Adds a small white reflection to give the eye a glossy appearance.
            pygame.draw.circle(surface, (255, 255, 255),
                               (int(pupil_x - 1), int(pupil_y - 2)),
                               max(1, eye_r // 3))

        # ---- دهان ----
        # خط افقی زیر چشم‌ها محل دهان مار را مشخص می‌کند.
        # Draws the horizontal mouth line beneath the eyes.
        mouth_y = hy + hw * 0.55
        pygame.draw.line(surface, dark,
                         (int(hx - hw * 0.3), int(mouth_y)),
                         (int(hx + hw * 0.3), int(mouth_y)), 2)

        # ---- ۲ نیش ----
        # دو مثلث باریک در دو طرف دهان، نیش‌های مار را تشکیل می‌دهند.
        # Draws two narrow triangular fangs on either side of the mouth.
        fang_y = mouth_y + 2
        for sign in (-1, 1):
            fx = hx + sign * hw * 0.2
            fang_pts = [
                (fx - 2, fang_y),
                (fx + 2, fang_y),
                (fx, fang_y + hw * 0.25),
            ]
            pygame.draw.polygon(surface, (255, 255, 255), fang_pts)
            pygame.draw.polygon(surface, dark, fang_pts, 1)

        # ---- زبان چنگالی ----
        # موج سینوسی، حرکت ظریف زبان را در طول زمان شبیه‌سازی می‌کند.
        # Uses a sine wave to simulate subtle tongue movement over time.
        tongue_wave = math.sin(self._t * 12) * 3
        tongue_base_y = hy + hw * 0.9
        tongue_tip_y = tongue_base_y + 10

        pygame.draw.line(surface, (255, 60, 60),
                         (int(hx), int(tongue_base_y)),
                         (int(hx + tongue_wave), int(tongue_tip_y - 4)), 2)

        # دو شاخه‌ی انتهایی، شکل چنگالی زبان را ایجاد می‌کنند.
        # The two terminal branches create the forked shape of the tongue.
        pygame.draw.line(surface, (255, 60, 60),
                         (int(hx + tongue_wave), int(tongue_tip_y - 4)),
                         (int(hx + tongue_wave - 4), int(tongue_tip_y)), 1)
        pygame.draw.line(surface, (255, 60, 60),
                         (int(hx + tongue_wave), int(tongue_tip_y - 4)),
                         (int(hx + tongue_wave + 4), int(tongue_tip_y)), 1)


__all__ = ["SerpentEnemy"]
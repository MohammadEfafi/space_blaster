"""
entities/enemies/titan.py
========================

TITAN — غول زره‌پوش (نسخه‌ی نهایی).

ظاهر: غول با ۶ پای مفصلی، بدنه‌ی بیضی زره‌پوش، هسته‌ی راکتور غول‌پیکر،
پنل‌های زره با خطوط زرد هشدار، چراغ‌های قرمز.
"""

from __future__ import annotations

import math
import random
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


class TitanEnemy(Enemy):
    """TITAN — غول زره‌پوش."""

    KIND = EnemyKind.TITAN

    # ویژگی‌های پایه‌ی تایتان، از جمله مقاومت، سرعت، امتیاز و تنظیمات شلیک.
    # Titan's base attributes, including health, speed, score, and shooting parameters.
    HP = 10
    RADIUS = 30
    SPEED = 35
    SCORE = 100
    DROP_CHANCE = 0.50
    SHOOT_CD = 3.0
    BULLET_SPEED = 180
    BODY_COLOR = (200, 180, 60)

    def _configure(self) -> None:
        # برای هر پا یک فاز تصادفی در نظر گرفته می‌شود تا حرکت پاها کاملاً هم‌زمان نباشد.
        # A random phase is assigned to each leg to prevent all legs from moving in sync.
        self._leg_phases = [random.uniform(0, math.tau) for _ in range(6)]

        # زمان مستقل ضربان هسته‌ی راکتور برای کنترل انیمیشن نور آن.
        # Independent reactor heartbeat timer used to control its glowing animation.
        self._heartbeat = 0.0

    def update_ai(self, dt: float) -> None:
        # حرکت عمودی دشمن متناسب با زمان سپری‌شده از فریم.
        # Vertical enemy movement scaled by the elapsed frame time.
        self.y += self.SPEED * dt

        # نوسان افقی ملایم حول موقعیت پایه‌ی دشمن.
        # Gentle horizontal oscillation around the enemy's base position.
        self.x = self._base_x + math.sin(self._t * 0.5) * 20.0

        # به‌روزرسانی زمان ضربان راکتور مستقل از فاز حرکت پاها انجام می‌شود.
        # The reactor heartbeat timer is updated independently of the leg movement phases.
        self._heartbeat += dt * 4.0

        # فاز حرکتی هر شش پا به‌صورت جداگانه جلو می‌رود.
        # The movement phase of each of the six legs advances independently.
        for i in range(6):
            self._leg_phases[i] += dt * 5.0

    def _do_shoot(self) -> list:
        # در صورت نبود صحنه، امکان ایجاد و ثبت مین وجود ندارد.
        # A mine cannot be created or registered when the scene is unavailable.
        if self.scene is None:
            return []

        # کلاس Bomb به‌صورت محلی وارد می‌شود تا وابستگی آن فقط در زمان اجرای این مسیر ایجاد شود.
        # Bomb is imported locally so its dependency is introduced only when this execution path is used.
        try:
            from entities.bullet import Bomb

            # مین در پایین بدنه‌ی تایتان ایجاد می‌شود و با سرعت عمودی مشخص حرکت می‌کند.
            # The mine is created below Titan's hull and moves with a defined vertical velocity.
            mine = Bomb(
                self.x, self.y + self.radius * 0.5,
                0, 60,
                scene=self.scene,
            )

            # شعاع و وضعیت اولیه‌ی اختصاصی مین تایتان تنظیم می‌شوند.
            # Titan mine's radius and initial internal state are configured.
            mine.radius = 12
            mine._bomb_age = 0.0
            mine._titan_mine = True

            # مین به صحنه اضافه می‌شود و هم‌زمان افکت صوتی و لرزش دوربین اجرا می‌شوند.
            # The mine is added to the scene, followed by the shooting sound and camera shake.
            self.scene.spawn_bullet(mine)
            self.scene.audio.play("enemy_shoot")
            self.scene.camera.shake(3.0)
            return [mine]

        # خطاهای احتمالی در ساخت مین یا اجرای افکت‌ها باعث توقف روند بازی نمی‌شوند.
        # Potential errors during mine creation or effect playback do not interrupt the game.
        except Exception:
            pass
        return []



    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        # شعاع ترسیم برای تعیین ابعاد اجزای ظاهری تایتان استفاده می‌شود.
        # The drawing radius is used to determine the dimensions of Titan's visual components.
        r = int(self.radius * 1.2)
        cx, cy = int(self.x), int(self.y)

        # رنگ پایه و طیف‌های تیره و روشن آن برای تفکیک لایه‌های بدنه آماده می‌شوند.
        # The base color and its darker and lighter variants are prepared to distinguish the hull layers.
        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 120)
        darker = self._darker(base, 180)
        bright = self._lighter(base, 70)

        # رنگ‌های ثابت مورد استفاده برای هاله‌ی راکتور و جزئیات هشدار.
        # Fixed colors used for the reactor glow and warning details.
        glow = (255, 240, 100)
        warn_yellow = (255, 210, 60)

        # ---- ۱. سایه‌ی غول‌پیکر ----
        # ---- 1. Massive shadow ----
        # سطح شفاف سایه متناسب با ابعاد تایتان ساخته می‌شود.
        # The transparent shadow surface is sized relative to Titan's dimensions.
        sw, sh = int(r * 1.7), int(r * 0.45)
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)

        # بیضی‌های تو در تو با شفافیت تدریجی، سایه‌ای نرم در زیر دشمن ایجاد می‌کنند.
        # Nested ellipses with gradually changing transparency create a soft shadow beneath the enemy.
        for rr in range(sh, 0, -1):
            a = int(120 * (1 - rr / sh) ** 1.5)
            if a > 0:
                pygame.draw.ellipse(shadow, (0, 0, 0, a),
                                    (sw - rr, sh - rr, rr * 2, rr * 2))
        surface.blit(shadow, (cx - sw, cy + int(r * 0.6) - sh))

        # ---- ۲. هاله‌ی زرد ملایم ----
        # ---- 2. Soft yellow aura ----
        # هاله‌ی دایره‌ای بزرگ با آلفای متغیر از مرکز به بیرون محو می‌شود.
        # A large circular aura fades outward with gradually changing alpha.
        aura_r = int(r * 1.5)
        aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
        for rr in range(aura_r, 0, -5):
            a = int(30 * (1 - rr / aura_r) ** 2)
            if a > 0:
                pygame.draw.circle(aura, (*glow, a), (aura_r, aura_r), rr)
        surface.blit(aura, (cx - aura_r, cy - aura_r),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # ---- ۳. ۶ پای مفصلی (زاویه‌دار) ----
        # ---- 3. Six articulated legs (angled) ----
        # هر پا با زاویه‌ی اختصاصی خود در اطراف بدنه قرار می‌گیرد.
        # Each leg is positioned around the hull using its own calculated angle.
        for i in range(6):
            # زاویه‌ی هر پا (سه‌تا در هر طرف)
            # Leg angle (three on each side)
            # سه پای هر سمت با اختلاف زاویه‌ای مشخص، آرایش متقارن پاها را تشکیل می‌دهند.
            # Three legs on each side form a symmetrical arrangement with defined angular offsets.
            if i < 3:
                angle = math.pi * 0.85 + (i * 0.35) + math.pi * 0.15
            else:
                angle = math.pi * 0.05 - ((i - 3) * 0.35) - math.pi * 0.15

            # جابه‌جایی تناوبی پا از فاز مستقل همان پا محاسبه می‌شود.
            # Periodic leg displacement is calculated from that leg's independent phase.
            wave = math.sin(self._leg_phases[i]) * 5

            # سه‌بخشی: ران، ساق، پا
            # Three segments: thigh, shin, and foot
            # مختصات مفصل‌ها و انتهای پا با زاویه‌ی آن و اندازه‌ی بدنه محاسبه می‌شوند.
            # Joint and foot coordinates are calculated from the leg angle and hull size.
            hip_x = cx + math.cos(angle) * r * 0.55
            hip_y = cy + int(r * 0.15) + math.sin(angle) * r * 0.15

            knee_x = cx + math.cos(angle) * r * 1.0
            knee_y = cy + int(r * 0.35) + math.sin(angle) * r * 0.3 + wave

            ankle_x = cx + math.cos(angle) * r * 1.2
            ankle_y = cy + int(r * 0.7) + wave

            foot_x = cx + math.cos(angle) * r * 1.4
            foot_y = cy + int(r * 0.9) + wave

            # ران (ضخیم)
            # Thigh (thick)
            # ضخامت بیشتر بخش ابتدایی پا، اتصال مستحکم آن به بدنه را نشان می‌دهد.
            # The thicker upper segment visually represents the leg's strong attachment to the hull.
            pygame.draw.line(surface, darker,
                             (int(hip_x), int(hip_y)),
                             (int(knee_x), int(knee_y)), 8)

            # ساق (متوسط)
            # Shin (medium thickness)
            pygame.draw.line(surface, dark,
                             (int(knee_x), int(knee_y)),
                             (int(ankle_x), int(ankle_y)), 6)

            # پا (نازک)
            # Foot segment (thin)
            pygame.draw.line(surface, base,
                             (int(ankle_x), int(ankle_y)),
                             (int(foot_x), int(foot_y)), 4)

            # خط روشن روی ساق
            # Highlight line on the shin
            # خط باریک روشن، بخش میانی پا را از سطح تیره‌ی آن متمایز می‌کند.
            # A thin bright line distinguishes the middle leg segment from its darker surface.
            pygame.draw.line(surface, bright,
                             (int(knee_x), int(knee_y)),
                             (int(ankle_x), int(ankle_y)), 1)

            # مفصل زانو
            # Knee joint
            # دایره‌ی بیرونی روشن و حاشیه‌ی داخلی، ظاهر یک مفصل مکانیکی را ایجاد می‌کنند.
            # The bright outer circle and inner outline create the appearance of a mechanical joint.
            pygame.draw.circle(surface, bright, (int(knee_x), int(knee_y)), 4)
            pygame.draw.circle(surface, base, (int(knee_x), int(knee_y)), 4, 1)

            # مفصل مچ
            # Ankle joint
            pygame.draw.circle(surface, bright, (int(ankle_x), int(ankle_y)), 3)

            # پنجه‌ی پا (مثلث)
            # Foot tip (triangle)
            # انتهای پا با رنگ هشدار مشخص می‌شود و حاشیه‌ی تیره آن را برجسته می‌کند.
            # The foot tip is highlighted with a warning color and emphasized by its dark outline.
            pygame.draw.circle(surface, warn_yellow, (int(foot_x), int(foot_y)), 4)
            pygame.draw.circle(surface, dark, (int(foot_x), int(foot_y)), 4, 1)

        # ---- ۴. بدنه‌ی بیضی غول‌پیکر ----
        # ---- 4. Massive elliptical hull ----
        # مستطیل مرجع برای تعیین محدوده و ابعاد بیضی اصلی بدنه.
        # Reference rectangle defining the bounds and dimensions of the main elliptical hull.
        body_rect = pygame.Rect(cx - r, cy - int(r * 0.85), r * 2, int(r * 1.6))

        # لایه‌ی سایه
        # Shadow layer
        # جابه‌جایی مستطیل به پایین، سایه‌ای جدا از سطح اصلی بدنه ایجاد می‌کند.
        # Moving the rectangle downward creates a shadow separate from the main hull surface.
        shadow_rect = body_rect.move(0, 4)
        pygame.draw.ellipse(surface, darker, shadow_rect)

        # بدنه‌ی اصلی
        # Main hull
        # بیضی تیره به‌عنوان لایه‌ی زیرین بدنه ترسیم می‌شود.
        # The dark ellipse is drawn as the underlying hull layer.
        pygame.draw.ellipse(surface, dark, body_rect)

        # لایه‌ی میانی (روشن‌تر)
        # Middle layer (lighter)
        # کوچک‌کردن مستطیل، بیضی داخلی را ایجاد می‌کند تا سطح مرکزی بدنه روشن‌تر باشد.
        # Shrinking the rectangle creates an inner ellipse that gives the central hull surface a lighter appearance.
        mid_rect = body_rect.inflate(-int(r * 0.2), -int(r * 0.2))
        pygame.draw.ellipse(surface, base, mid_rect)

        # خط نئونی دور
        # Neon outline
        pygame.draw.ellipse(surface, bright, body_rect, 3)

        # ---- ۵. خطوط هشدار زرد-مشکی روی بدنه ----
        # ---- 5. Yellow-black warning lines on the hull ----
        # نوارهای زرد عمودی
        # Vertical yellow stripes
        # تقسیم عرض بدنه به پنج بخش، محل چهار نوار هشدار را تعیین می‌کند.
        # Dividing the hull width into five sections determines the positions of the four warning stripes.
        for i in range(4):
            t = (i + 1) / 5
            stripe_x = body_rect.left + int(body_rect.width * t)
            pygame.draw.line(surface, warn_yellow,
                             (stripe_x, body_rect.top + 8),
                             (stripe_x, body_rect.bottom - 8), 2)

        # ---- ۶. پنل‌های زره (بیضی کناری) ----
        # ---- 6. Armor panels (side ellipses) ----
        # پنل‌ها در دو طرف بدنه و با ابعاد یکسان قرار می‌گیرند.
        # The panels are positioned on both sides of the hull with matching dimensions.
        for sign in (-1, 1):
            panel_x = cx + sign * int(r * 0.55)
            panel_y = cy - int(r * 0.05)
            panel_w = int(r * 0.35)
            panel_h = int(r * 0.85)
            panel_rect = pygame.Rect(panel_x - panel_w // 2, panel_y - panel_h // 2,
                                     panel_w, panel_h)

            # سطح تیره و حاشیه‌ی روشن، محدوده‌ی هر پنل را از بدنه جدا می‌کنند.
            # The dark fill and bright outline distinguish each panel from the main hull.
            pygame.draw.ellipse(surface, darker, panel_rect)
            pygame.draw.ellipse(surface, bright, panel_rect, 2)

            # خطوط افقی روی پنل
            # Horizontal panel lines
            # سه خط داخلی، جزئیات سطح زره را نمایش می‌دهند.
            # Three internal lines add detail to the armored surface.
            for j in range(3):
                ly = panel_rect.top + int(panel_rect.height * (0.3 + j * 0.25))
                pygame.draw.line(surface, bright,
                                 (panel_rect.left + 3, ly),
                                 (panel_rect.right - 3, ly), 1)

            # نقطه‌ی درخشان وسط پنل
            # Glowing point at the center of the panel
            pygame.draw.circle(surface, warn_yellow,
                               (panel_x, panel_y), 3)

        # ---- ۷. هسته‌ی راکتور غول‌پیکر ----
        # ---- 7. Massive reactor core ----
        # موقعیت هسته کمی بالاتر از مرکز بدنه است و اندازه‌ی آن با ضربان تغییر می‌کند.
        # The core is positioned slightly above the hull center, and its size changes with the heartbeat.
        core_y = cy - int(r * 0.05)
        pulse = 0.7 + 0.3 * math.sin(self._heartbeat)
        core_r = int(r * 0.32 * pulse)

        # هاله‌ی بزرگ
        # Large glow
        # حلقه‌های شفاف با شعاع کاهشی، هاله‌ی نورانی اطراف راکتور را ایجاد می‌کنند.
        # Transparent circles with decreasing radii create the luminous aura around the reactor.
        for rr in range(int(r * 0.7), 0, -3):
            a = int(160 * (1 - rr / (r * 0.7)) ** 1.5 * pulse)
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*glow, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, core_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # هسته (سه لایه)
        # Core (three layers)
        # سه دایره‌ی هم‌مرکز، از لایه‌ی بیرونی تا مرکز سفید، شدت نور متفاوتی دارند.
        # Three concentric circles have different brightness levels, from the outer layer to the white center.
        pygame.draw.circle(surface, (200, 100, 20), (cx, core_y), core_r + 3)
        pygame.draw.circle(surface, glow, (cx, core_y), core_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, core_y), max(3, core_r // 2))

        # حلقه‌ی چرخان دور هسته
        # Rotating ring around the core
        # شش نشانگر با فاصله‌ی زاویه‌ای مساوی روی یک مسیر بیضی‌شکل حرکت می‌کنند.
        # Six markers move along an elliptical path with equal angular spacing.
        ring_r = int(r * 0.5)
        for i in range(6):
            angle = self._t * 2 + i * math.tau / 6
            rx = cx + int(math.cos(angle) * ring_r)
            ry = core_y + int(math.sin(angle) * ring_r * 0.7)

            # هر نشانگر یک نقطه‌ی زرد با مرکز روشن‌تر است.
            # Each marker is a yellow dot with a brighter center.
            pygame.draw.circle(surface, warn_yellow, (rx, ry), 3)
            pygame.draw.circle(surface, (255, 255, 200), (rx, ry), 1)

        # ---- ۸. چراغ‌های هشدار قرمز ----
        # ---- 8. Red warning lights ----
        # شدت نور چراغ‌ها با تابع سینوسی تغییر می‌کند تا حالت چشمک‌زن داشته باشند.
        # The lights' intensity changes sinusoidally to produce a blinking effect.
        blink = 0.5 + 0.5 * math.sin(self._t * 6)

        # چراغ‌ها در دو طرف بخش بالایی بدنه به‌صورت قرینه قرار دارند.
        # The lights are positioned symmetrically on both sides of the upper hull.
        for sign in (-1, 1):
            lx = cx + sign * int(r * 0.65)
            ly = cy - int(r * 0.65)
            a = int(240 * blink)

            # در صورت وجود شدت نور مثبت، هاله و چراغ مرکزی ترسیم می‌شوند.
            # The glow and central light are drawn when the calculated intensity is positive.
            if a > 0:
                g = pygame.Surface((16, 16), pygame.SRCALPHA)
                for rr in range(8, 0, -2):
                    aa = int(a * (1 - rr / 8))
                    if aa > 0:
                        pygame.draw.circle(g, (255, 60, 60, aa), (8, 8), rr)
                surface.blit(g, (lx - 8, ly - 8),
                             special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, (255, 100, 100), (lx, ly), 3)

        # ---- ۹. نوار HP (بزرگ) ----
        # ---- 9. Large HP bar ----
        # نوار سلامتی تنها پس از دریافت آسیب نمایش داده می‌شود.
        # The health bar is displayed only after the enemy has taken damage.
        if self.hp < self.max_hp:
            w = int(r * 2.2)
            h = 7
            x = cx - w // 2
            y = cy - int(r * 1.05)

            # پس‌زمینه‌ی تیره و نیمه‌شفاف، خوانایی نوار را روی تصویر حفظ می‌کند.
            # The dark, semi-transparent background keeps the bar readable against the scene.
            bg = pygame.Surface((w + 6, h + 6), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 240))
            surface.blit(bg, (x - 3, y - 3))

            # نسبت سلامتی برای تعیین طول بخش پرشده‌ی نوار محاسبه می‌شود.
            # The health ratio determines the filled portion of the bar.
            ratio = max(0.0, self.hp / self.max_hp)

            # رنگ نوار متناسب با میزان سلامتی از سبز به زرد و سپس قرمز تغییر می‌کند.
            # The bar color changes from green to yellow and then red according to the remaining health.
            color = (80, 255, 140) if ratio > 0.5 else (255, 220, 60) if ratio > 0.25 else (255, 60, 60)
            pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
            pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 2)



__all__ = ["TitanEnemy"]
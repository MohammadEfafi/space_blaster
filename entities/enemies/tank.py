"""
entities/enemies/tank.py
========================

دشمن نوع دوم — SIEGE CRAWLER (خزنده‌ی محاصره) — نسخه‌ی بازطراحی‌شده.

طراحی جدید (سفینه‌ی جنگی سنگین):
    • بدنه‌ی کشیده و پهن (مثل ناوچه‌ی فضایی)
    • دو پاد سلاح مدرن با دهانه‌ی چرخان درخشان
    • بال‌های زره‌ای با خطوط نئونی
    • هسته‌ی انرژی مرکزی با خطوط شعاعی
    • صفحه‌ی شیشه‌ای (کابین) در جلو
    • چراغ‌های هشدار چشمک‌زن
    • نوار HP در بالا (بعد از آسیب)

رفتار:
    • کند، مقاوم (HP=4)
    • شلیک دوگانه از پادهای سلاح
    • نوسان افقی ملایم
"""

from __future__ import annotations

import math
import pygame

from core import settings as S
from entities.bullet import Bullet, BulletKind
from entities.enemies.base import Enemy, EnemyKind


class TankEnemy(Enemy):
    """SIEGE CRAWLER — ناوچه‌ی جنگی سنگین."""

    KIND = EnemyKind.TANK

    # ویژگی‌های پایه و تنظیمات شلیک مستقیماً از پیکربندی مرکزی دشمن دریافت می‌شوند.
    # Base attributes and shooting parameters are loaded directly from the central enemy configuration.
    HP           = S.EnemyCfg.Tank.HP
    RADIUS       = S.EnemyCfg.Tank.RADIUS
    SPEED        = S.EnemyCfg.Tank.SPEED
    SCORE        = S.EnemyCfg.Tank.SCORE
    DROP_CHANCE  = S.EnemyCfg.Tank.DROP_CHANCE
    SHOOT_CD     = S.EnemyCfg.Tank.SHOOT_CD
    BULLET_SPEED = S.EnemyCfg.Tank.BULLET_SPEED
    BODY_COLOR   = S.Palette.ENEMY_TANK



    def update_ai(self, dt: float) -> None:
        # حرکت عمودی با توجه به سرعت دشمن و مدت‌زمان سپری‌شده از فریم انجام می‌شود.
        # Vertical movement is scaled by the enemy speed and the elapsed frame time.
        self.y += self.SPEED * dt

        # نوسان سینوسی موقعیت افقی حول نقطه‌ی پایه‌ی حرکت دشمن.
        # Sinusoidal horizontal movement around the enemy's base position.
        self.x = self._base_x + math.sin(self._t * 0.9) * 14.0



    def _do_shoot(self) -> list[Bullet]:
        # بدون دسترسی به صحنه، امکان ایجاد و ثبت گلوله وجود ندارد.
        # Bullets cannot be created and registered without access to the scene.
        if self.scene is None:
            return []

        # بازیکن از صحنه دریافت می‌شود؛ در صورت نبودن یا از بین رفتن او، شلیک انجام نمی‌شود.
        # The player is retrieved from the scene; shooting is skipped if the player is missing or no longer alive.
        player = getattr(self.scene, "player", None)
        if player is None or not player.alive:
            return []

        # بردار جهت از موقعیت دشمن به سمت بازیکن محاسبه می‌شود.
        # The direction vector is calculated from the enemy's position toward the player.
        dx = player.x - self.x
        dy = player.y - self.y

        # فاصله برای نرمال‌سازی بردار استفاده می‌شود؛ مقدار جایگزین از تقسیم بر صفر جلوگیری می‌کند.
        # The distance is used to normalize the vector; the fallback value prevents division by zero.
        d = math.hypot(dx, dy) or 1.0
        ux, uy = dx / d, dy / d

        # بردار عمود بر جهت هدف، محل خروج دو گلوله را در دو طرف محور شلیک تعیین می‌کند.
        # A perpendicular vector to the target direction determines the two bullet spawn positions on either side of the firing axis.
        px, py = -uy, ux

        bullets: list[Bullet] = []

        # دو گلوله با فاصله‌ی جانبی یکسان و جهت حرکت مشترک ایجاد می‌شوند.
        # Two bullets are created with equal lateral offsets and the same movement direction.
        for side in (-1.0, 1.0):
            bx = self.x + px * 16 * side
            by = self.y + py * 16 * side
            bullets.append(Bullet(
                bx, by,
                ux * self.BULLET_SPEED, uy * self.BULLET_SPEED,
                friendly=False, kind=BulletKind.ENEMY, scene=self.scene,
            ))

        # ثبت گلوله‌ها در صحنه و پخش صدای شلیک در یک بلوک محافظت‌شده انجام می‌شود.
        # Bullet registration in the scene and shooting sound playback are performed inside a protected block.
        try:
            for b in bullets:
                self.scene.spawn_bullet(b)
            self.scene.audio.play("enemy_shoot")
        except Exception:
            # خطاهای هنگام ثبت گلوله یا پخش صدا مانع ادامه‌ی اجرای بازی نمی‌شوند.
            # Errors during bullet registration or sound playback do not interrupt the game.
            pass

        return bullets



    def draw_body(self, surface: pygame.Surface, alpha: int = 255) -> None:
        # شعاع ترسیم از شعاع اصلی دشمن بزرگ‌تر در نظر گرفته می‌شود تا اجزای ظاهری جا بگیرند.
        # The drawing radius is larger than the enemy's base radius to accommodate its visual components.
        r = max(12, int(self.radius * 1.2))
        cx, cy = int(self.x), int(self.y)

        # نسخه‌های تیره و روشن رنگ پایه برای سایه‌پردازی و ایجاد کنتراست آماده می‌شوند.
        # Darker and lighter variants of the base color are prepared for shading and contrast.
        base = self.tint(self.BODY_COLOR)
        dark = self._darker(base, 100)
        darker = self._darker(base, 150)
        bright = self._lighter(base, 70)

        # ---- ۱. سایه‌ی زیر (شناور) ----
        # ---- 1. Ground shadow (hovering effect) ----
        self._draw_ground_shadow(surface, cx, cy, r)

        # ---- ۲. بال‌های زره‌ای دو طرف ----
        # ---- 2. Armored wings on both sides ----
        self._draw_armored_wings(surface, cx, cy, r, dark, brighter := self._lighter(base, 40))

        # ---- ۳. پادهای سلاح مدرن (کناری) ----
        # ---- 3. Modern weapon pods (side-mounted) ----
        self._draw_weapon_pods(surface, cx, cy, r, dark, bright)

        # ---- ۴. بدنه‌ی اصلی (کشیده) ----
        # ---- 4. Main elongated hull ----
        self._draw_hull(surface, cx, cy, r, base, dark, bright)

        # ---- ۵. کابین شیشه‌ای (جلو) ----
        # ---- 5. Glass cockpit (front) ----
        self._draw_cockpit(surface, cx, cy, r)

        # ---- ۶. هسته‌ی انرژی مرکزی ----
        # ---- 6. Central energy core ----
        self._draw_energy_core(surface, cx, cy, r)

        # ---- ۷. خطوط نئونی روی بدنه ----
        # ---- 7. Neon lines on the hull ----
        self._draw_panel_lines(surface, cx, cy, r, bright)

        # ---- ۸. چراغ‌های هشدار ----
        # ---- 8. Warning lights ----
        self._draw_warning_lights(surface, cx, cy, r)

        # نوار سلامتی فقط زمانی نمایش داده می‌شود که دشمن آسیب دیده باشد.
        # The health bar is displayed only when the enemy has taken damage.
        if self.max_hp > 1 and self.hp < self.max_hp:
            self._draw_hp_bar(surface, cx, cy, r)

        # ---- ۱۰. فید ----
        # ---- 10. Fade effect ----
        if alpha < 250:
            self._apply_fade(surface, cx, cy, r, alpha)



    def _draw_ground_shadow(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        # ابعاد سطح شفاف سایه متناسب با شعاع دشمن تعیین می‌شود.
        # The transparent shadow surface dimensions are determined relative to the enemy radius.
        sw = int(r * 1.5)
        sh = int(r * 0.4)
        shadow = pygame.Surface((sw * 2, sh * 2), pygame.SRCALPHA)

        # بیضی‌های تو در تو با آلفای تدریجی، سایه‌ای نرم و محوشونده ایجاد می‌کنند.
        # Nested ellipses with gradually changing alpha create a soft, fading shadow.
        for rr in range(sh, 0, -1):
            a = int(90 * (1 - rr / sh) ** 1.6)
            if a <= 0:
                continue
            pygame.draw.ellipse(shadow, (0, 0, 0, a),
                                (sw - rr, sh - rr, rr * 2, rr * 2))

        # سایه کمی پایین‌تر از مرکز دشمن قرار می‌گیرد تا حالت شناور القا شود.
        # The shadow is positioned slightly below the enemy's center to create a hovering effect.
        surface.blit(shadow, (cx - sw, cy + int(r * 0.55) - sh))

    def _draw_armored_wings(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        dark: tuple[int, int, int],
        mid: tuple[int, int, int],
    ) -> None:
        """بال‌های زره‌ای پهن با لبه‌های نئونی."""
        # بال‌ها به‌صورت قرینه در دو طرف بدنه ساخته می‌شوند.
        # The wings are constructed symmetrically on both sides of the hull.
        for sign in (-1, 1):
            wing = [
                (cx + sign * int(r * 0.35), cy - int(r * 0.55)),
                (cx + sign * int(r * 1.35), cy - int(r * 0.35)),
                (cx + sign * int(r * 1.30), cy + int(r * 0.40)),
                (cx + sign * int(r * 0.85), cy + int(r * 0.55)),
                (cx + sign * int(r * 0.35), cy + int(r * 0.35)),
            ]

            # سطح تیره، حجم بال را تشکیل می‌دهد و خط روشن، مرز آن را مشخص می‌کند.
            # The dark fill forms the wing body, while the bright outline defines its edges.
            pygame.draw.polygon(surface, dark, wing)
            pygame.draw.polygon(surface, mid, wing, 2)

            # خطوط زره‌ای روی بال
            # Armor panel lines on the wing
            # خطوط موازی روی سطح بال، جزئیات صفحات زرهی را نمایش می‌دهند.
            # Parallel lines across the wing surface represent its armored panels.
            for i in range(3):
                y_off = -0.35 + i * 0.3
                pygame.draw.line(
                    surface, mid,
                    (cx + sign * int(r * 0.55), cy + int(r * y_off)),
                    (cx + sign * int(r * 1.15), cy + int(r * y_off * 0.9)),
                    1,
                )

            # نوک درخشان بال (چراغ ناوبری)
            # Glowing wing tip (navigation light)
            # رنگ چراغ برای دو بال متفاوت است و فاز چشمک‌زدن آن‌ها نیز اختلاف دارد.
            # Each wing has a different navigation light color, and their blinking phases are offset.
            tip_x = cx + sign * int(r * 1.30)
            tip_y = cy + int(r * 0.05)
            color = (255, 80, 80) if sign < 0 else (80, 255, 120)
            blink = 0.5 + 0.5 * math.sin(self._t * 4.0 + (0 if sign < 0 else math.pi))
            a = int(200 * blink)

            # شدت هاله از مقدار موجی blink گرفته می‌شود و به‌صورت افزایشی روی تصویر ترکیب می‌شود.
            # The glow intensity is derived from the blink waveform and additively blended onto the image.
            if a > 0:
                glow = pygame.Surface((14, 14), pygame.SRCALPHA)
                for rr in range(7, 0, -2):
                    aa = int(a * (1 - rr / 7))
                    if aa > 0:
                        pygame.draw.circle(glow, (*color, aa), (7, 7), rr)
                surface.blit(glow, (tip_x - 7, tip_y - 7),
                             special_flags=pygame.BLEND_RGBA_ADD)
                pygame.draw.circle(surface, color, (tip_x, tip_y), 3)

    def _draw_weapon_pods(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """پادهای سلاح مدرن — استوانه‌ای با دهانه‌ی چرخان درخشان."""
        # دو پاد سلاح در دو سمت بدنه و با ساختار یکسان ترسیم می‌شوند.
        # Two weapon pods are drawn on opposite sides of the hull using the same structure.
        for sign in (-1, 1):
            px = cx + sign * int(r * 0.65)
            py = cy + int(r * 0.35)

            # ---- بدنه‌ی پاد (استوانه) ----
            # ---- Pod body (cylinder) ----
            # ابعاد پاد با شعاع دشمن مقیاس می‌شوند و حداقل اندازه‌ی مشخصی دارند.
            # Pod dimensions scale with the enemy radius while maintaining minimum sizes.
            pod_w = max(6, int(r * 0.28))
            pod_h = max(12, int(r * 0.55))
            pod_rect = pygame.Rect(
                px - pod_w, py, pod_w * 2, pod_h,
            )

            # سایه
            # Shadow
            pygame.draw.rect(surface, dark,
                             pod_rect.move(0, 2), border_radius=4)

            # بدنه
            # Body
            pygame.draw.rect(surface, (30, 30, 50),
                             pod_rect, border_radius=4)
            pygame.draw.rect(surface, bright, pod_rect, 2, border_radius=4)

            # خطوط فنری روی پاد
            # Ribbed lines on the pod
            # خطوط عرضی، ظاهر قطعه‌قطعه و زرهی بدنه‌ی پاد را تقویت می‌کنند.
            # Transverse lines reinforce the pod's segmented, armored appearance.
            for i in range(3):
                ly = py + int(pod_h * (0.25 + i * 0.25))
                pygame.draw.line(surface, bright,
                                 (px - pod_w, ly), (px + pod_w, ly), 1)

            # ---- دهانه‌ی چرخان (درخشان) ----
            # ---- Rotating glowing muzzle ----
            tip_y = py + pod_h
            tip_r = max(4, int(r * 0.16))

            # هاله
            # Glow
            # دایره‌های شفاف با اندازه‌های کاهشی، درخشش پیرامون دهانه را می‌سازند.
            # Transparent circles of decreasing size create the glow around the muzzle.
            for rr in range(tip_r * 3, 0, -1):
                a = int(120 * (1 - rr / (tip_r * 3)))
                if a <= 0:
                    continue
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 100, 220, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (px - rr * 2, tip_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

            # حلقه‌ی چرخان
            # Rotating ring
            # شش نقطه با اختلاف زاویه‌ی ثابت روی یک مسیر دایره‌ای حرکت می‌کنند.
            # Six points move along a circular path with equal angular spacing.
            for i in range(6):
                angle = self._t * 5.0 + i * math.tau / 6
                dx = int(math.cos(angle) * tip_r * 0.85)
                dy = int(math.sin(angle) * tip_r * 0.85)
                pygame.draw.circle(surface, (255, 200, 240),
                                   (px + dx, tip_y + dy), 1)

            # هسته‌ی مرکزی
            # Central core
            # دو دایره‌ی هم‌مرکز، هسته‌ی روشن دهانه را با یک مرکز درخشان‌تر نمایش می‌دهند.
            # Two concentric circles render the muzzle core with a brighter center.
            pygame.draw.circle(surface, (255, 130, 240),
                               (px, tip_y), tip_r)
            pygame.draw.circle(surface, (255, 240, 255),
                               (px, tip_y), max(1, tip_r // 2))

    def _draw_hull(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        base: tuple[int, int, int],
        dark: tuple[int, int, int],
        bright: tuple[int, int, int],
    ) -> None:
        """بدنه‌ی اصلی کشیده (مثل ناوچه)."""
        # نقاط چندضلعی، فرم کشیده‌ی بدنه و نوک‌های باریک آن را مشخص می‌کنند.
        # The polygon vertices define the elongated hull and its tapered ends.
        hull = [
            (cx - int(r * 0.5),  cy - int(r * 0.75)),   # بالا-چپ
            (cx,                  cy - int(r * 0.90)),  # بالا (نوک)
            (cx + int(r * 0.5),  cy - int(r * 0.75)),   # بالا-راست
            (cx + int(r * 0.65), cy - int(r * 0.30)),   # شانه راست
            (cx + int(r * 0.55), cy + int(r * 0.55)),   # پایین-راست
            (cx,                  cy + int(r * 0.85)),  # نوک پایین
            (cx - int(r * 0.55), cy + int(r * 0.55)),   # پایین-چپ
            (cx - int(r * 0.65), cy - int(r * 0.30)),   # شانه چپ
        ]

        # سایه
        # Shadow
        # جابه‌جایی عمودی نقاط، سایه‌ای باریک در زیر بدنه ایجاد می‌کند.
        # A vertical offset of the vertices creates a narrow shadow beneath the hull.
        shadow = [(x, y + 3) for (x, y) in hull]
        pygame.draw.polygon(surface, dark, shadow)

        # بدنه (دو لایه)
        # Hull (two layers)
        # ابتدا شکل اصلی با رنگ پایه پر می‌شود تا لایه‌ی زیرین بدنه ساخته شود.
        # The main shape is first filled with the base color to create the hull's underlying layer.
        pygame.draw.polygon(surface, base, hull)

        # لایه‌ی میانی روشن‌تر
        # Lighter middle layer
        # چندضلعی داخلی، سطح روشن‌تری در مرکز بدنه ایجاد می‌کند و از یکنواختی رنگ می‌کاهد.
        # The inner polygon creates a brighter central surface and reduces color uniformity.
        mid = [
            (cx - int(r * 0.35), cy - int(r * 0.55)),
            (cx,                  cy - int(r * 0.75)),
            (cx + int(r * 0.35), cy - int(r * 0.55)),
            (cx + int(r * 0.40), cy + int(r * 0.25)),
            (cx,                  cy + int(r * 0.55)),
            (cx - int(r * 0.40), cy + int(r * 0.25)),
        ]
        pygame.draw.polygon(surface, self._lighter(base, 40), mid)

        # خط نئونی دور
        # Neon outline
        # ترسیم مجدد چندضلعی بدون پرکردن، لبه‌ی بیرونی بدنه را برجسته می‌کند.
        # Redrawing the polygon without filling it highlights the outer hull boundary.
        pygame.draw.polygon(surface, bright, hull, 2)

    def _draw_cockpit(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """کابین شیشه‌ای (جلو، رو به پایین)."""
        # موقعیت و ابعاد کابین نسبت به مرکز و شعاع بدنه تعیین می‌شوند.
        # The cockpit position and dimensions are calculated relative to the hull center and radius.
        cab_y = cy + int(r * 0.35)
        cab_w = max(5, int(r * 0.30))
        cab_h = max(4, int(r * 0.15))

        # کابین با یک بیضی تیره و حاشیه‌ی روشن نمایش داده می‌شود.
        # The cockpit is represented by a dark ellipse with a bright outline.
        rect = pygame.Rect(cab_x := cx - cab_w, cab_y - cab_h, cab_w * 2, cab_h * 2)
        pygame.draw.ellipse(surface, (20, 60, 100), rect)
        pygame.draw.ellipse(surface, (100, 220, 255), rect, 2)

        # درخشش داخلی
        # Inner highlight
        # کوچک‌کردن مستطیل اصلی، محدوده‌ی داخلی کابین را برای لایه‌ی روشن‌تر مشخص می‌کند.
        # Shrinking the original rectangle defines the cockpit's inner area for the brighter layer.
        inner = rect.inflate(-4, -4)
        pygame.draw.ellipse(surface, (60, 160, 220), inner)

        # خط بازتاب
        # Reflection line
        # قوس روشن، بازتاب نور روی سطح شیشه‌ای کابین را شبیه‌سازی می‌کند.
        # The bright arc simulates light reflecting off the cockpit glass.
        pygame.draw.arc(surface, (200, 250, 255), inner, 0.3, 2.0, 1)

    def _draw_energy_core(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """هسته‌ی انرژی مرکزی با خطوط شعاعی."""
        # هسته در نزدیکی مرکز بدنه قرار دارد و اندازه‌ی آن با یک تابع تناوبی تغییر می‌کند.
        # The core is positioned near the hull center, and its size changes periodically.
        core_y = cy - int(r * 0.10)
        pulse = 0.7 + 0.3 * math.sin(self._t * 6.0)
        core_r = max(3, int(r * 0.22 * pulse))

        # خطوط شعاعی (از مرکز به بیرون)
        # Radial lines (from the center outward)
        # شش خط با فاصله‌ی زاویه‌ای مساوی، هم‌زمان با زمان بازی حول هسته می‌چرخند.
        # Six equally spaced lines rotate around the core over time.
        for i in range(6):
            angle = self._t * 1.2 + i * math.tau / 6
            x1 = cx + int(math.cos(angle) * (core_r + 3))
            y1 = core_y + int(math.sin(angle) * (core_r + 3))
            x2 = cx + int(math.cos(angle) * (core_r + 10))
            y2 = core_y + int(math.sin(angle) * (core_r + 10))
            a = int(140 * pulse)

            # هر خط روی سطح شفافی با ابعاد متناسب با مختصات ابتدا و انتهای آن رسم می‌شود.
            # Each line is drawn on a transparent surface sized according to its start and end coordinates.
            if a > 0:
                line_surf = pygame.Surface((abs(x2 - x1) + 4, abs(y2 - y1) + 4), pygame.SRCALPHA)
                ox = min(x1, x2) - 2
                oy = min(y1, y2) - 2
                pygame.draw.line(line_surf, (255, 150, 240, a),
                                 (x1 - ox, y1 - oy), (x2 - ox, y2 - oy), 1)
                surface.blit(line_surf, (ox, oy))

        # هاله
        # Glow
        # گرادیان دایره‌ای با شفافیت وابسته به pulse، شدت نور هسته را با ضربان آن هماهنگ می‌کند.
        # A circular gradient with pulse-dependent transparency synchronizes the core glow with its pulsing.
        glow_size = int(r * 0.5)
        glow = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
        for rr in range(glow_size, 0, -2):
            a = int(150 * (1 - rr / glow_size) * pulse)
            if a <= 0:
                continue
            pygame.draw.circle(glow, (255, 100, 220, a),
                               (glow_size, glow_size), rr)
        surface.blit(glow, (cx - glow_size, core_y - glow_size),
                     special_flags=pygame.BLEND_RGBA_ADD)

        # هسته
        # Core
        # دایره‌ی بیرونی و مرکز روشن‌تر، بخش اصلی هسته‌ی انرژی را تشکیل می‌دهند.
        # The outer circle and its brighter center form the main energy core.
        pygame.draw.circle(surface, (255, 130, 230), (cx, core_y), core_r)
        pygame.draw.circle(surface, (255, 240, 255), (cx, core_y), max(1, core_r // 2))

    def _draw_panel_lines(
        self,
        surface: pygame.Surface,
        cx: int, cy: int, r: int,
        bright: tuple[int, int, int],
    ) -> None:
        """خطوط نئونی افقی روی بدنه."""
        # سه خط در ارتفاع‌های متفاوت، جزئیات پنل‌های سطح بدنه را نمایش می‌دهند.
        # Three lines at different heights represent the hull's surface panel details.
        for i, y_off in enumerate((-0.45, -0.15, 0.15)):
            y = cy + int(r * y_off)

            # طول خطوط به‌تدریج کاهش می‌یابد تا با محدوده‌ی داخلی بدنه هماهنگ باشد.
            # Line lengths gradually decrease to remain within the hull's inner area.
            w = int(r * (0.35 - i * 0.05))
            pygame.draw.line(surface, bright,
                             (cx - w, y), (cx + w, y), 1)

    def _draw_warning_lights(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        """چراغ‌های هشدار کوچک روی بدنه."""
        # شدت نور چراغ‌ها با موج سینوسی تغییر می‌کند و حالت چشمک‌زن ایجاد می‌شود.
        # The lights' intensity changes with a sine wave to create a blinking effect.
        blink = 0.5 + 0.5 * math.sin(self._t * 6.0)

        # دو چراغ در دو طرف بخش بالایی بدنه به‌صورت قرینه قرار می‌گیرند.
        # Two lights are positioned symmetrically on either side of the upper hull.
        for sign in (-1, 1):
            lx = cx + sign * int(r * 0.25)
            ly = cy - int(r * 0.55)
            a = int(200 * blink)
            if a <= 0:
                continue

            # هاله‌ی قرمز با چند دایره‌ی شفاف و شدت نور تدریجی ساخته می‌شود.
            # A red glow is created using multiple transparent circles with gradually changing intensity.
            glow = pygame.Surface((10, 10), pygame.SRCALPHA)
            for rr in range(5, 0, -1):
                aa = int(a * (1 - rr / 5))
                if aa > 0:
                    pygame.draw.circle(glow, (255, 60, 60, aa), (5, 5), rr)
            surface.blit(glow, (lx - 5, ly - 5),
                         special_flags=pygame.BLEND_RGBA_ADD)

            # نقطه‌ی مرکزی روشن، محل اصلی چراغ هشدار را مشخص می‌کند.
            # A bright central dot marks the actual warning light position.
            pygame.draw.circle(surface, (255, 100, 100), (lx, ly), 2)

    def _draw_hp_bar(
        self, surface: pygame.Surface, cx: int, cy: int, r: int,
    ) -> None:
        # ابعاد نوار و موقعیت آن در بالای بدنه تعیین می‌شوند.
        # The health bar dimensions and its position above the hull are determined here.
        w = int(r * 1.8)
        h = 5
        x = cx - w // 2
        y = cy - int(r * 0.95) - 14

        # پس‌زمینه‌ی نیمه‌شفاف باعث می‌شود نوار سلامتی روی اجزای پشت آن خوانا باشد.
        # The semi-transparent background keeps the health bar readable over underlying elements.
        bg = pygame.Surface((w + 4, h + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        surface.blit(bg, (x - 2, y - 2))

        # نسبت سلامتی محدود می‌شود تا مقدار پرشدگی از بازه‌ی صفر تا یک خارج نشود.
        # The health ratio is clamped so the fill amount stays within the zero-to-one range.
        ratio = max(0.0, self.hp / self.max_hp)

        # رنگ نوار با کاهش سلامتی از سبز به زرد و سپس قرمز تغییر می‌کند.
        # The bar color changes from green to yellow and then red as health decreases.
        color = (80, 255, 140) if ratio > 0.5 else (255, 220, 60) if ratio > 0.25 else (255, 60, 60)
        pygame.draw.rect(surface, color, (x, y, int(w * ratio), h))
        pygame.draw.rect(surface, (255, 255, 255), (x, y, w, h), 1)



__all__ = ["TankEnemy"]
"""
entities/player/vanguard.py
===========================

سفینه‌ی VANGUARD — پیشتاز سنگین و مقاوم.

سبک بازی:
    • بیشترین HP (۵)
    • کندترین سفینه
    • شلیک دوگانه‌ی همزمان (دو گلوله‌ی موازی)
    • مناسب بازیکن‌هایی که می‌خوان با قدرت پیش برن

ظاهر:
    بدنه‌ی پهن و ضخیم با زره چندلایه،
    دو توپ شلیک در دو طرف،
    کابین شیشه‌ای پهن،
    رنگ سبز-طلایی نظامی.
"""

from __future__ import annotations

import math

import pygame

from core import settings as S
from entities.bullet import BulletKind
from entities.player.base import Player


class Vanguard(Player):
    """پیشتاز سنگین — کند، مقاوم، پر قدرت."""

    # ---- شناسه ----
    NAME        = "VANGUARD"
    DESCRIPTION = "Heavy armor, slow pace. Stand your ground."
    KIND_KEY    = "vanguard"

    # ---- آمار (سنگین و مقاوم) ----
    MAX_HP:        int   = 6           # بیشترین جان
    SPEED:         float = 260.0       # کند
    RADIUS:        float = 24.0        # بزرگ‌تر
    INVULN_TIME:   float = 1.4         # کمی کمتر (چون جان زیاد داره)
    SHOOT_CD:      float = 0.15        # کندتر شلیک
    BULLET_SPEED:  float = 680.0
    BULLET_DAMAGE: int   = 1
    BULLET_KIND:   BulletKind = BulletKind.PLAYER

    # فیزیک سنگین (شتاب کم، میرایی زیاد — حس وزن)
    ACCEL: float = 6.0
    DRAG:  float = 6.5

    # ---- رنگ‌ها ----
    PRIMARY_COLOR:   tuple[int, int, int] = (80, 200, 120)     # سبز نظامی
    SECONDARY_COLOR: tuple[int, int, int] = (30, 90, 60)
    ACCENT_COLOR:    tuple[int, int, int] = (255, 200, 60)     # طلایی
    HIGHLIGHT_COLOR: tuple[int, int, int] = (220, 255, 230)
    FLAME_COLOR:     tuple[int, int, int] = (255, 180, 60)

    def _get_shot_angles(self) -> list[float]:
        # هنگام فعال بودن Power-Up، پنج زاویه برای شلیک گسترده‌تر برمی‌گرداند.
        # Returns five firing angles to create a wider spread while the Power-Up is active.
        if self.powerup_time > 0.0:
            return [-108.0, -99.0, -90.0, -81.0, -72.0]

        # در حالت عادی، زاویه‌ی شلیک مستقیم به سمت بالای صفحه است.
        # Uses a straight upward firing angle during normal shooting.
        return [-90.0] 

    def try_shoot(self):
        """
        Override برای اضافه کردن offset افقی به دو گلوله.
        گلوله‌ی اول از پاد چپ، گلوله‌ی دوم از پاد راست.
        """
        from entities.bullet import Bullet
        import math

        # در زمان Cooldown یا پس از نابودی سفینه، شلیک جدید انجام نمی‌شود.
        # Prevents firing while the weapon is on cooldown or the ship is no longer alive.
        if self.shoot_cd > 0.0 or not self.alive:
            return []

        # وضعیت شلیک، فلش دهانه و پس‌زنی سفینه را برای شلیک جدید تنظیم می‌کند.
        # Updates the firing cooldown, muzzle flash, and ship recoil for the new shot.
        self.shoot_cd = self.current_shoot_cd
        self.muzzle_flash = 1.0
        self.recoil = 0.7

        bullets = []
        r = self.radius

        # ---- Power-Up: پنج‌گانه ----
        # در حالت Power-Up، پنج گلوله با زاویه‌های متفاوت به‌صورت پخش‌شونده شلیک می‌شوند.
        # During the Power-Up, fires five bullets at different angles in a spread pattern.
        if self.powerup_time > 0.0:
            angles = [-108.0, -99.0, -90.0, -81.0, -72.0]
            for angle_deg in angles:
                # زاویه‌ی هر گلوله را به رادیان تبدیل می‌کند تا در محاسبات مثلثاتی قابل استفاده باشد.
                # Converts each bullet angle to radians for trigonometric calculations.
                a = math.radians(angle_deg)

                # مؤلفه‌های افقی و عمودی سرعت را بر اساس زاویه‌ی شلیک محاسبه می‌کند.
                # Calculates the horizontal and vertical velocity components from the firing angle.
                vx = math.cos(a) * self.BULLET_SPEED
                vy = math.sin(a) * self.BULLET_SPEED

                # نقطه‌ی شروع گلوله را در امتداد بردار شلیک و کمی بیرون از بدنه قرار می‌دهد.
                # Positions the bullet spawn point along the firing direction, just outside the ship's body.
                ox = math.cos(a) * (r + 6)
                oy = math.sin(a) * (r + 6)

                # گلوله را با مشخصات سفینه و ارجاع صحنه ایجاد کرده و به فهرست شلیک‌ها اضافه می‌کند.
                # Creates a bullet using the ship's settings and scene reference, then adds it to the firing list.
                bullets.append(Bullet(
                    self.x + ox, self.y + oy,
                    vx, vy,
                    friendly=True,
                    kind=self.BULLET_KIND,
                    damage=self.BULLET_DAMAGE,
                    scene=self.scene,
                ))
        else:
            # ---- دو گلوله از پادهای کناری ----
            # در حالت عادی، دو گلوله از دو پاد متقارن در طرفین بدنه شلیک می‌شوند.
            # In normal mode, two bullets are fired from symmetrical weapon pods on either side of the hull.
            pod_offsets = [-r * 0.65, r * 0.65]
            for pod_x_offset in pod_offsets:
                bullets.append(Bullet(
                    self.x + pod_x_offset,
                    self.y - (r + 4),
                    0.0, -self.BULLET_SPEED,
                    friendly=True,
                    kind=self.BULLET_KIND,
                    damage=self.BULLET_DAMAGE,
                    scene=self.scene,
                ))

        # اگر سفینه به صحنه متصل باشد، صدای شلیک را پخش می‌کند.
        # Plays the firing sound when the ship is attached to a scene.
        if self.scene is not None:
            try:
                self.scene.audio.play("player_shoot")
            except Exception:
                # خطای پخش صدا مانع ادامه‌ی اجرای منطق شلیک نمی‌شود.
                # Prevents an audio playback error from interrupting the firing logic.
                pass

        return bullets

    def get_engine_offsets(self) -> list[tuple[float, float, float]]:
        # سه نقطه‌ی خروج شعله‌ی موتور را با فاصله و شدت متفاوت زیر بدنه مشخص می‌کند.
        # Defines three engine flame positions beneath the hull, each with a different offset and intensity.
        return [
            (-0.55, 0.95, 0.75),
            ( 0.00, 1.05, 1.00),
            ( 0.55, 0.95, 0.75),
        ]

    def draw_ship(self, surface: pygame.Surface, cx: int, cy: int) -> None:
        # شعاع سفینه و رنگ‌های موردنیاز برای ترسیم اجزای مختلف را آماده می‌کند.
        # Prepares the ship radius and colors used to render its different components.
        r = int(self.radius)
        primary = self.PRIMARY_COLOR
        secondary = self.SECONDARY_COLOR
        highlight = self.HIGHLIGHT_COLOR
        accent = self.ACCENT_COLOR

        # ---- ۱. سایه‌ی زیر (عمق) ----
        # چندضلعی سایه را کمی پایین‌تر از بدنه قرار می‌دهد تا عمق بصری ایجاد شود.
        # Offsets the shadow polygon slightly below the hull to create visual depth.
        shadow_pts = [
            (cx - int(r * 0.85), cy - int(r * 0.80) + 2),
            (cx - int(r * 1.05), cy + int(r * 0.75) + 2),
            (cx + int(r * 1.05), cy + int(r * 0.75) + 2),
            (cx + int(r * 0.85), cy - int(r * 0.80) + 2),
        ]
        pygame.draw.polygon(surface, (10, 40, 20), shadow_pts)

        # ---- ۲. بال‌های پهن و ضخیم ----
        # بال چپ — با یک پله برای حس زره
        # نقاط بال چپ را تعریف می‌کند؛ شکل چندضلعی و پهن آن ظاهر زره‌پوش ایجاد می‌کند.
        # Defines the left wing vertices; its broad polygon shape creates an armored appearance.
        left_wing = [
            (cx - int(r * 0.50), cy - int(r * 0.70)),   # بالا-داخلی
            (cx - int(r * 1.05), cy - int(r * 0.50)),   # پله‌ی بالا
            (cx - int(r * 1.15), cy + int(r * 0.30)),   # نوک چپ
            (cx - int(r * 0.95), cy + int(r * 0.70)),   # پایین-چپ
            (cx - int(r * 0.40), cy + int(r * 0.55)),   # پایین-داخلی
        ]

        # مختصات بال راست را با قرینه‌سازی افقی نقاط بال چپ محاسبه می‌کند.
        # Calculates the right wing coordinates by mirroring the left wing horizontally.
        right_wing = [(cx + (cx - x), y) for (x, y) in left_wing]

        # ابتدا سطح داخلی هر دو بال و سپس خطوط پیرامونی آن‌ها را ترسیم می‌کند.
        # Draws the inner fill of both wings first, followed by their outlines.
        pygame.draw.polygon(surface, secondary, left_wing)
        pygame.draw.polygon(surface, secondary, right_wing)
        pygame.draw.polygon(surface, primary, left_wing, 2)
        pygame.draw.polygon(surface, primary, right_wing, 2)

        # ---- ۳. نوارهای زره روی بال‌ها ----
        # با استفاده از علامت‌های منفی و مثبت، جزئیات زره را به‌صورت متقارن روی دو بال رسم می‌کند.
        # Uses negative and positive signs to draw symmetrical armor details across both wings.
        for sign in (-1, 1):
            # خط طولی روی بال
            pygame.draw.line(
                surface, highlight,
                (cx + sign * int(r * 0.70), cy - int(r * 0.40)),
                (cx + sign * int(r * 0.90), cy + int(r * 0.55)),
                2,
            )
            # خط عرضی کوتاه
            pygame.draw.line(
                surface, accent,
                (cx + sign * int(r * 0.65), cy - int(r * 0.25)),
                (cx + sign * int(r * 0.95), cy - int(r * 0.25)),
                1,
            )

        # ---- ۴. پادهای سلاح (توپ‌ها) ----
        # اجزای دو پاد سلاح را با موقعیت، ابعاد و جزئیات یکسان در دو طرف بدنه ترسیم می‌کند.
        # Renders the two weapon pods with matching positions, dimensions, and details on either side of the hull.
        for sign in (-1, 1):
            pod_x = cx + sign * int(r * 0.65)
            pod_y = cy - int(r * 0.30)
            pod_w = max(4, int(r * 0.22))
            pod_h = max(6, int(r * 0.40))

            # مستطیل بدنه‌ی پاد را ایجاد کرده و سطح و حاشیه‌ی آن را رسم می‌کند.
            # Creates the pod body rectangle and draws its fill and outline.
            rect = pygame.Rect(
                pod_x - pod_w, pod_y - pod_h // 2,
                pod_w * 2, pod_h,
            )
            pygame.draw.rect(surface, secondary, rect)
            pygame.draw.rect(surface, highlight, rect, 2)

            # نوک درخشان (لوله)
            # محل دهانه‌ی هر توپ را مشخص کرده و با دو دایره، جلوه‌ی درخشان آن را ایجاد می‌کند.
            # Positions each cannon muzzle and creates its glowing effect using two circles.
            tip_y = pod_y - pod_h // 2 - 3
            pygame.draw.circle(surface, accent, (pod_x, tip_y), max(2, int(r * 0.10)))
            pygame.draw.circle(surface, (255, 255, 220), (pod_x, tip_y), max(1, int(r * 0.05)))

        # ---- ۵. بدنه‌ی اصلی — ذوزنقه‌ی پهن ----
        # رأس‌های بدنه‌ی اصلی را تعریف می‌کند؛ فرم پهن آن با طراحی سنگین سفینه هماهنگ است.
        # Defines the main hull vertices; its wide shape reinforces the ship's heavy design.
        hull = [
            (cx,                  cy - int(r * 0.90)),   # بالا
            (cx - int(r * 0.55),  cy - int(r * 0.70)),   # چپ بالا
            (cx - int(r * 0.60),  cy + int(r * 0.65)),   # چپ پایین
            (cx,                  cy + int(r * 0.90)),   # دنباله‌ی وسط
            (cx + int(r * 0.60),  cy + int(r * 0.65)),
            (cx + int(r * 0.55),  cy - int(r * 0.70)),
        ]

        # سطح بدنه را با رنگ اصلی و حاشیه‌ی آن را با رنگ روشن ترسیم می‌کند.
        # Draws the hull fill using the primary color and outlines it with the highlight color.
        pygame.draw.polygon(surface, primary, hull)
        pygame.draw.polygon(surface, highlight, hull, 2)

        # ---- ۶. پنل زره میانی (روشن‌تر) ----
        # چندضلعی پنل مرکزی را کوچک‌تر از بدنه تعریف می‌کند تا لایه‌ی دوم زره مشخص شود.
        # Defines a central panel smaller than the hull to represent a second armor layer.
        armor_panel = [
            (cx,                  cy - int(r * 0.80)),
            (cx - int(r * 0.35),  cy - int(r * 0.50)),
            (cx - int(r * 0.40),  cy + int(r * 0.30)),
            (cx,                  cy + int(r * 0.55)),
            (cx + int(r * 0.40),  cy + int(r * 0.30)),
            (cx + int(r * 0.35),  cy - int(r * 0.50)),
        ]

        # پنل زره را با رنگ روشن‌تر پر می‌کند و حاشیه‌ی ظریفی برای تفکیک آن از بدنه می‌کشد.
        # Fills the armor panel with a lighter color and adds a subtle outline to distinguish it from the hull.
        pygame.draw.polygon(surface, (120, 230, 150), armor_panel)
        pygame.draw.polygon(surface, highlight, armor_panel, 1)

        # ---- ۷. خط عمودی میانی ----
        # یک خط در امتداد محور مرکزی بدنه رسم می‌کند تا جزئیات ساختاری آن بیشتر نمایان شود.
        # Draws a line along the hull's central axis to emphasize its structural details.
        pygame.draw.line(
            surface, secondary,
            (cx, cy - int(r * 0.75)),
            (cx, cy + int(r * 0.85)),
            2,
        )

        # ---- ۸. کابین پهن (شیشه‌ای) ----
        # ابعاد و موقعیت کابین بیضی‌شکل را متناسب با شعاع سفینه محاسبه می‌کند.
        # Calculates the elliptical cockpit dimensions and position relative to the ship radius.
        cab_w = max(4, int(r * 0.32))
        cab_h = max(3, int(r * 0.18))
        cab_y = cy - int(r * 0.35)
        cab_rect = pygame.Rect(
            cx - cab_w, cab_y - cab_h,
            cab_w * 2, cab_h * 2,
        )

        # لایه‌ی بیرونی کابین را رسم می‌کند تا قاب و سطح اصلی آن شکل بگیرد.
        # Draws the cockpit's outer layer to establish its frame and main surface.
        pygame.draw.ellipse(surface, secondary, cab_rect)
        pygame.draw.ellipse(surface, accent, cab_rect, 2)

        # با کوچک کردن مستطیل، سطح داخلی شیشه را جدا کرده و با رنگ روشن رسم می‌کند.
        # Shrinks the rectangle to isolate the inner glass area and renders it with a lighter color.
        inner_rect = cab_rect.inflate(-2, -2)
        pygame.draw.ellipse(surface, (200, 250, 210), inner_rect)

        # ---- ۹. خطوط زره افقی ----
        # سه خط افقی با موقعیت و طول متفاوت روی بدنه رسم می‌کند تا ظاهر لایه‌لایه‌ی زره تقویت شود.
        # Draws three horizontal lines with varying positions and lengths to reinforce the layered armor appearance.
        for i, y_off in enumerate([-0.20, 0.15, 0.45]):
            y = cy + int(r * y_off)
            w = int(r * (0.50 - i * 0.08))
            pygame.draw.line(
                surface, highlight,
                (cx - w, y), (cx + w, y), 1,
            )

        # ---- ۱۰. نشان نظامی (ستاره‌ی کوچک) ----
        # موقعیت و اندازه‌ی نشان ستاره‌ای را بر اساس مرکز و شعاع سفینه تعیین می‌کند.
        # Determines the star emblem's position and size relative to the ship's center and radius.
        star_y = cy + int(r * 0.15)
        size = max(3, int(r * 0.15))
        pts = []

        # پنج رأس بیرونی و پنج رأس داخلی را به‌صورت یکی‌درمیان محاسبه می‌کند تا یک ستاره‌ی پنج‌پر بسازد.
        # Calculates five outer and five inner vertices alternately to construct a five-pointed star.
        for i in range(5):
            a_out = -math.pi / 2 + i * 2 * math.pi / 5
            a_in = a_out + math.pi / 5
            pts.append((cx + math.cos(a_out) * size, star_y + math.sin(a_out) * size))
            pts.append((cx + math.cos(a_in) * size * 0.45, star_y + math.sin(a_in) * size * 0.45))

        # چندضلعی حاصل را با رنگ تأکیدی رسم می‌کند تا نشان نظامی روی بدنه دیده شود.
        # Draws the resulting polygon with the accent color to display the military emblem on the hull.
        pygame.draw.polygon(surface, accent, pts)

        # ---- ۱۱. چراغ‌های ناوبری (کمی متفاوت با Interceptor) ----
        # مقدار blink با تابع سینوسی بین صفر و یک نوسان می‌کند و برای چشمک‌زدن متناوب چراغ‌ها استفاده می‌شود.
        # The sinusoidal blink value oscillates between zero and one to create alternating navigation lights.
        blink = 0.5 + 0.5 * math.sin(self._t * 4.0)

        # چراغ چپ و راست را با رنگ‌های متفاوت و شدت نور متضاد ترسیم می‌کند.
        # Renders the left and right navigation lights with different colors and opposing brightness levels.
        for sign, color in [(-1, (255, 80, 80)), (1, (80, 255, 120))]:
            tip_x = cx + sign * int(r * 1.05)
            tip_y = cy - int(r * 0.15)

            # شفافیت هر چراغ را بر اساس جهت آن و مقدار نوسان تعیین می‌کند.
            # Calculates each light's alpha based on its side and the current blink value.
            alpha = int(180 * (blink if sign < 0 else (1 - blink)))

            # یک سطح شفاف مستقل برای ترکیب نور چراغ با تصویر اصلی ایجاد می‌کند.
            # Creates a separate transparent surface for blending the navigation light with the main image.
            glow = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, alpha), (6, 6), 4)
            pygame.draw.circle(glow, (255, 255, 255, alpha), (6, 6), 2)

            # نور چراغ را با ترکیب افزایشی رنگ‌ها روی سطح اصلی قرار می‌دهد.
            # Adds the navigation light to the main surface using additive color blending.
            surface.blit(glow, (tip_x - 6, tip_y - 6),
                         special_flags=pygame.BLEND_RGBA_ADD)


__all__ = ["Vanguard"]
"""
entities/bullet.py
==================

سیستم گلوله‌ها (Bullets) برای SPACE BLASTER.

یک کلاس واحد که می‌تواند انواع مختلف گلوله را با پارامترهای متفاوت
مدیریت کند — از گلوله‌ی ساده‌ی پلیر تا شلیک سنگین باس. تفاوت‌ها فقط
در پیکربندی است، نه در کد.

ویژگی‌ها:
    • انواع گلوله با Enum (PLAYER, ENEMY, LASER, PLASMA, BOSS, HOMING)
    • دنباله‌ی درخشان (Trail) که به‌صورت خودکار و با عمر کم رسم می‌شود
    • هاله‌ی نور (Glow) با gradient ساده برای افکت نئونی
    • پشتیبانی از گلوله‌ی هدف‌گیر (Homing) با چرخش نرم
    • اندازه‌ی دینامیک، رنگ قابل تنظیم و damage قابل تعیین
    • بهینه‌سازی شده برای صدها گلوله‌ی همزمان در صفحه
"""

from __future__ import annotations

import math
from collections import deque
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

import pygame

from core import settings as S
from entities.entity import Entity

if TYPE_CHECKING:
    from scenes.gameplay import GameplayScene


class BulletKind(Enum):
    """دسته‌بندی گلوله‌ها برای رفتار و ظاهر متفاوت."""
    # هر عضو یک نوع گلوله را مشخص می‌کند و برای انتخاب تنظیمات و رفتار آن استفاده می‌شود.
    # Each member identifies a bullet type and is used to select its configuration and behavior.
    PLAYER  = auto()   # گلوله‌ی ساده‌ی پلیر
    ENEMY   = auto()   # گلوله‌ی معمولی دشمن
    LASER   = auto()   # خط پرسرعت، دمی بلند
    PLASMA  = auto()   # توپ پلاسما، کند ولی بزرگ
    BOSS    = auto()   # سنگین و درخشان
    HOMING  = auto()   # هدف‌گیر با چرخش نرم


class _BulletPreset:
    """مقادیر پیش‌فرض برای هر نوع گلوله."""
    # این کلاس تنظیمات ظاهری و رفتاری مشترک هر نوع گلوله را در یک ساختار نگه می‌دارد.
    # Stores the shared visual and behavioral settings for each bullet type in one structure.
    __slots__ = (
        "radius", "damage", "color_core", "color_glow",
        "trail_len", "trail_alpha", "homing_rate", "trail_width",
    )

    def __init__(
        self,
        radius: float,
        damage: int,
        color_core: tuple[int, int, int],
        color_glow: tuple[int, int, int],
        trail_len: int,
        trail_alpha: int,
        trail_width: int,
        homing_rate: float = 0.0,
    ) -> None:
        # مقادیر ورودی را در ویژگی‌های نمونه ذخیره می‌کند تا هنگام ساخت گلوله قابل استفاده باشند.
        # Stores the supplied values as instance attributes for use when creating bullets.
        self.radius = radius
        self.damage = damage
        self.color_core = color_core
        self.color_glow = color_glow
        self.trail_len = trail_len
        self.trail_alpha = trail_alpha
        self.trail_width = trail_width
        self.homing_rate = homing_rate


# تنظیمات پیش‌فرض هر نوع گلوله؛ کلاس Bullet بر اساس نوع انتخاب‌شده از این مقادیر استفاده می‌کند.
# Default settings for each bullet type; the Bullet class uses these values according to the selected type.
_PRESETS: dict[BulletKind, _BulletPreset] = {
    BulletKind.PLAYER: _BulletPreset(
        radius=4.0, damage=1,
        color_core=(240, 255, 255), color_glow=S.Palette.BULLET_PLAYER,
        trail_len=10, trail_alpha=170, trail_width=2,
    ),
    BulletKind.ENEMY: _BulletPreset(
        radius=4.5, damage=1,
        color_core=(255, 220, 220), color_glow=S.Palette.BULLET_ENEMY,
        trail_len=8, trail_alpha=150, trail_width=2,
    ),
    BulletKind.LASER: _BulletPreset(
        radius=3.0, damage=1,
        color_core=(255, 255, 255), color_glow=(120, 255, 240),
        trail_len=18, trail_alpha=200, trail_width=3,
    ),
    BulletKind.PLASMA: _BulletPreset(
        radius=7.0, damage=2,
        color_core=(255, 255, 220), color_glow=(255, 180, 40),
        trail_len=10, trail_alpha=140, trail_width=4,
    ),
    BulletKind.BOSS: _BulletPreset(
        radius=6.0, damage=1,
        color_core=(255, 230, 255), color_glow=S.Palette.BULLET_BOSS,
        trail_len=14, trail_alpha=180, trail_width=3,
    ),
    BulletKind.HOMING: _BulletPreset(
        radius=4.0, damage=1,
        color_core=(240, 255, 240), color_glow=(120, 255, 140),
        trail_len=14, trail_alpha=170, trail_width=2,
        homing_rate=4.5,
    ),
}


class Bullet(Entity):
    """
    یک گلوله‌ی قابل استفاده توسط پلیر یا دشمن.

    پارامترهای کلیدی:
        friendly    — True اگر به دشمن آسیب بزند (پلیر)؛ False اگر به پلیر
        kind        — نوع گلوله؛ پیش‌فرض بر اساس friendly
        damage      — مقدار آسیب؛ اگر None باشد از preset استفاده می‌شود
        target      — (اختیاری) هدف برای گلوله‌های HOMING
        pierce      — چند موجودیت را می‌تواند رد کند (0 = یکی و تمام)
        life        — حداکثر عمر (ثانیه)؛ پس از آن خودکار نابود می‌شود
    """

    # کش سراسری برای جلوگیری از ساخت مکرر Surface در هر فریم
    # کش مشترک بین تمام نمونه‌ها، سطح هاله‌ی ساخته‌شده را برای استفاده‌ی مجدد نگه می‌دارد.
    # Shared across all instances, this cache retains generated glow surfaces for reuse.
    _glow_cache: dict[tuple[int, int], pygame.Surface] = {}

    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        *,
        friendly: bool = True,
        kind: Optional[BulletKind] = None,
        damage: Optional[int] = None,
        scene: "GameplayScene | None" = None,
        target: Optional[Entity] = None,
        pierce: int = 0,
        life: float = 3.2,
    ) -> None:
        # اگر نوع گلوله مشخص نشده باشد، از روی friendly نوع پلیر یا دشمن را انتخاب می‌کند.
        # Selects the player or enemy bullet type from friendly when no explicit type is provided.
        if kind is None:
            kind = BulletKind.PLAYER if friendly else BulletKind.ENEMY

        # تنظیمات پایه‌ی نوع انتخاب‌شده را برای مقداردهی اولیه دریافت می‌کند.
        # Retrieves the selected bullet type's preset for initialization.
        preset = _PRESETS[kind]

        # بخش پایه‌ی Entity را با موقعیت، سرعت، شعاع و صحنه مقداردهی می‌کند.
        # Initializes the Entity base with position, velocity, radius, and scene.
        super().__init__(
            x, y,
            vx=vx, vy=vy,
            radius=preset.radius,
            hp=1,
            scene=scene,
        )

        # نوع، سمت شلیک، آسیب و محدودیت عبور گلوله از موجودیت‌ها را ذخیره می‌کند.
        # Stores the bullet type, allegiance, damage, and entity-piercing limit.
        self.kind: BulletKind = kind
        self.friendly: bool = friendly
        self.damage: int = preset.damage if damage is None else damage
        self.pierce: int = pierce
        self.life: float = float(life)
        self.max_life: float = float(life)

        # ---- هدف برای گلوله‌ی HOMING ----
        # مرجع هدف را برای استفاده در محاسبات هدایت گلوله نگه می‌دارد.
        # Retains the target reference for use in the bullet's homing calculations.
        self.target: Optional[Entity] = target

        # ---- دنباله‌ی درخشان ----
        # deque با maxlen ثابت — خودکار قدیمی‌ترین را حذف می‌کند
        # موقعیت‌های اخیر گلوله را با ظرفیت محدود نگه می‌دارد تا دنباله به‌صورت خودکار کوتاه بماند.
        # Stores recent bullet positions in a fixed-capacity deque so the trail remains automatically bounded.
        self._trail: deque[tuple[float, float]] = deque(maxlen=preset.trail_len)
        self._trail_alpha: int = preset.trail_alpha
        self._trail_width: int = preset.trail_width

        # ---- کش رنگ‌ها ----
        # رنگ هسته و هاله را از تنظیمات نوع گلوله دریافت می‌کند.
        # Retrieves the core and glow colors from the selected bullet preset.
        self._color_core: tuple[int, int, int] = preset.color_core
        self._color_glow: tuple[int, int, int] = preset.color_glow

        # ---- homing ----
        # نرخ تغییر جهت گلوله‌ی هدف‌گیر را از preset دریافت می‌کند.
        # Retrieves the homing bullet's steering rate from its preset.
        self._homing_rate: float = preset.homing_rate

    def on_spawn(self) -> None:
        """در لحظه‌ی ساخت، زاویه را از روی سرعت تعیین می‌کند."""
        # در صورت داشتن سرعت مؤثر، زاویه‌ی حرکت را از مؤلفه‌های سرعت محاسبه می‌کند.
        # Calculates the movement angle from the velocity components when the bullet has meaningful speed.
        if self.speed > 0.001:
            self.angle = math.degrees(math.atan2(self.vy, self.vx))

    def on_death(self) -> None:
        """هنگام نابودی، یک انفجار کوچک ذره‌ای در محل تولد می‌سازد."""
        # افکت برخورد را فقط زمانی ایجاد می‌کند که گلوله به یک صحنه متصل باشد.
        # Creates the impact effect only when the bullet is attached to a scene.
        if self.scene is not None:
            try:
                self.scene.spawn_bullet_impact(
                    self.x, self.y, self._color_glow, is_friendly=self.friendly
                )
            except Exception:
                # خطای ایجاد افکت نباید روند نابودی گلوله را مختل کند.
                # Prevents an impact-effect error from interrupting the bullet's destruction.
                pass

    def update_entity(self, dt: float) -> None:
        # ---- شمارش عمر ----
        # عمر باقی‌مانده‌ی گلوله را با توجه به زمان سپری‌شده کاهش می‌دهد.
        # Decreases the bullet's remaining lifetime according to the elapsed time.
        self.life -= dt
        if self.life <= 0:
            self.kill()
            return

        # ---- homing ----
        # فقط گلوله‌ی HOMING دارای هدف زنده، وارد منطق هدایت به سمت هدف می‌شود.
        # Only a HOMING bullet with a living target enters the target-steering logic.
        if self.kind == BulletKind.HOMING and self.target is not None and self.target.alive:
            self._steer_toward_target(dt)

        # ---- دنباله ----
        # موقعیت فعلی را به انتهای دنباله اضافه می‌کند تا مسیر حرکت قابل ترسیم باشد.
        # Appends the current position to the trail so the bullet's movement path can be rendered.
        self._trail.append((self.x, self.y))

        # ---- خارج از صفحه ----
        # گلوله‌ای که از محدوده‌ی قابل قبول صفحه خارج شده باشد، حذف می‌شود.
        # Removes bullets that have moved beyond the allowed screen bounds.
        if self.offscreen(margin=40):
            self.kill()
            return

        # ---- زاویه ----
        # زاویه‌ی فعلی را از سرعت به‌روزرسانی می‌کند تا جهت نمایش با مسیر حرکت هماهنگ بماند.
        # Updates the current angle from velocity so the displayed orientation follows the movement direction.
        if self.speed > 0.001:
            self.angle = math.degrees(math.atan2(self.vy, self.vx))

    def _steer_toward_target(self, dt: float) -> None:
        """چرخش نرم سرعت به سمت هدف (Homing)."""
        # در صورت نبود هدف، امکان محاسبه‌ی جهت هدایت وجود ندارد.
        # Steering cannot be calculated when no target is available.
        if self.target is None:
            return

        # بردار فاصله از گلوله تا هدف را محاسبه می‌کند.
        # Calculates the displacement vector from the bullet to its target.
        desired_x = self.target.x - self.x
        desired_y = self.target.y - self.y
        d = math.hypot(desired_x, desired_y)

        # اگر گلوله تقریباً به مرکز هدف رسیده باشد، از تقسیم بر فاصله‌ی ناچیز جلوگیری می‌کند.
        # Avoids division by a negligible distance when the bullet is already near the target's center.
        if d < 0.001:
            return

        # بردار فاصله را نرمال می‌کند تا فقط جهت هدف باقی بماند.
        # Normalizes the displacement vector so that only the target direction remains.
        desired_x /= d
        desired_y /= d

        # سرعت فعلی گلوله را برای حفظ اندازه‌ی بردار سرعت ذخیره می‌کند.
        # Stores the current bullet speed so the velocity magnitude can be preserved.
        sp = self.speed
        if sp < 0.001:
            return

        # جهت حرکت فعلی را از مؤلفه‌های سرعت به دست می‌آورد.
        # Derives the current movement direction from the velocity components.
        cur_x = self.vx / sp
        cur_y = self.vy / sp

        # میان‌یابی خطی بین جهت فعلی و جهت مطلوب
        # میزان تغییر جهت را با زمان فریم و نرخ هدایت محدود می‌کند تا چرخش نرم انجام شود.
        # Limits the steering interpolation using frame time and homing rate for smooth turning.
        t = min(1.0, self._homing_rate * dt)

        # جهت فعلی را به اندازه‌ی t به سمت جهت هدف جابه‌جا می‌کند.
        # Moves the current direction toward the target direction by the interpolation factor t.
        nx = cur_x + (desired_x - cur_x) * t
        ny = cur_y + (desired_y - cur_y) * t

        # جهت جدید را نرمال می‌کند و در سرعت قبلی ضرب می‌کند تا اندازه‌ی سرعت تغییر نکند.
        # Normalizes the new direction and scales it by the previous speed to preserve speed magnitude.
        n = math.hypot(nx, ny) or 1.0
        self.vx = (nx / n) * sp
        self.vy = (ny / n) * sp

    def draw_entity(self, surface: pygame.Surface) -> None:
        # اگر عمر گلوله داره تموم می‌شه، کمی محو شو (fade-out نرم)
        # شفافیت گلوله را در لحظات پایانی عمر به‌تدریج کاهش می‌دهد.
        # Gradually reduces the bullet's opacity during the final moments of its lifetime.
        fade = 1.0
        if self.life < 0.35:
            fade = max(0.0, self.life / 0.35)
        alpha = int(255 * fade)

        # ---- دنباله ----
        # دنباله را با شفافیت متناسب با وضعیت فعلی گلوله رسم می‌کند.
        # Draws the trail using opacity adjusted to the bullet's current fade level.
        self._draw_trail(surface, alpha)

        # ---- هاله ----
        # هاله‌ی نور را در اطراف گلوله رسم می‌کند.
        # Renders the glow around the bullet.
        self._draw_glow(surface, alpha)

        # ---- هسته ----
        # رنگ هسته را با tint موجودیت هماهنگ و شعاع و مختصات رسم را آماده می‌کند.
        # Applies the entity tint to the core color and prepares its radius and drawing coordinates.
        core_color = self.tint(self._color_core)
        r = max(1, int(round(self.radius)))
        cx, cy = self.pos_int

        # برای گلوله‌های تقریباً کاملاً مات، رسم مستقیم سریع‌تر است.
        # Uses direct drawing for bullets that are almost fully opaque.
        if alpha >= 250:
            pygame.draw.circle(surface, core_color, (cx, cy), r)
        else:
            # رسم نیمه‌شفاف با استفاده از Surface موقت
            # برای پشتیبانی از آلفا، هسته روی یک سطح شفاف جداگانه رسم و سپس ترکیب می‌شود.
            # Supports alpha by drawing the core on a separate transparent surface before compositing it.
            size = r * 2 + 4
            tmp = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(tmp, (*core_color, alpha), (size // 2, size // 2), r)
            surface.blit(tmp, (cx - size // 2, cy - size // 2))

    def _draw_trail(self, surface: pygame.Surface, base_alpha: int) -> None:
        # برای رسم خط دنباله حداقل دو موقعیت ثبت‌شده لازم است.
        # At least two recorded positions are required to draw a trail segment.
        if len(self._trail) < 2:
            return

        # موقعیت‌های ثبت‌شده را به فهرست تبدیل می‌کند تا دسترسی و پیمایش آن‌ها ساده باشد.
        # Converts the recorded positions to a list for convenient access and iteration.
        pts = list(self._trail)
        n = len(pts)

        # bound box محاسبه کن
        # محدوده‌ی مستطیلی دنباله را با در نظر گرفتن حاشیه‌ی ضخامت خطوط محاسبه می‌کند.
        # Calculates the trail's bounding rectangle, including padding for line thickness.
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        pad = self._trail_width + 4
        min_x = int(min(xs)) - pad
        min_y = int(min(ys)) - pad
        max_x = int(max(xs)) + pad
        max_y = int(max(ys)) + pad
        w = max_x - min_x
        h = max_y - min_y

        # از ساخت سطحی با ابعاد نامعتبر جلوگیری می‌کند.
        # Prevents creating a surface with invalid dimensions.
        if w <= 0 or h <= 0:
            return

        # سطح شفاف محدود به محدوده‌ی دنباله ایجاد می‌کند تا نیازی به رسم روی کل صفحه نباشد.
        # Creates a transparent surface limited to the trail bounds, avoiding full-screen drawing.
        tmp = pygame.Surface((w, h), pygame.SRCALPHA)

        # هر دو نقطه‌ی متوالی را به یک قطعه‌ی دنباله تبدیل می‌کند.
        # Converts each pair of consecutive points into a trail segment.
        for i in range(n - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]

            # با افزایش i، شفافیت و ضخامت خط بیشتر می‌شود تا انتهای نزدیک‌تر به گلوله پررنگ‌تر باشد.
            # Increases line opacity and width with i so the trail becomes stronger toward the bullet.
            t = (i + 1) / (n - 1)
            a = int(self._trail_alpha * t * (base_alpha / 255.0))
            if a <= 0:
                continue
            lw = max(1, int(self._trail_width * t))
            color = (*self._color_glow, a)

            # مختصات جهانی را به مختصات محلی سطح موقت تبدیل کرده و قطعه‌ی دنباله را رسم می‌کند.
            # Converts world coordinates to the temporary surface's local coordinates and draws the trail segment.
            pygame.draw.line(
                tmp, color,
                (int(x1 - min_x), int(y1 - min_y)),
                (int(x2 - min_x), int(y2 - min_y)),
                lw,
            )

        # دنباله‌ی رسم‌شده را در محل محدوده‌ی اصلی روی صفحه قرار می‌دهد.
        # Blits the rendered trail onto the main surface at its original bounds.
        surface.blit(tmp, (min_x, min_y))

    def _draw_glow(self, surface: pygame.Surface, alpha: int) -> None:
        """رسم هاله‌ی نرم با استفاده از کش سطح."""
        # شعاع هاله را متناسب با اندازه‌ی گلوله محاسبه می‌کند.
        # Calculates the glow radius relative to the bullet's size.
        r = int(self.radius * 2.6)
        if r < 2:
            return

        # کلید کش را از شعاع و رنگ هاله می‌سازد تا سطح مناسب برای این ترکیب بازیابی شود.
        # Builds a cache key from the glow radius and color to retrieve the matching surface.
        key = (r, hash(self._color_glow))
        glow = Bullet._glow_cache.get(key)

        # اگر سطحی برای این ترکیب وجود نداشته باشد، گرادیان هاله را یک‌بار می‌سازد و ذخیره می‌کند.
        # If no surface exists for this combination, generates the glow gradient once and caches it.
        if glow is None:
            size = r * 2
            glow = pygame.Surface((size, size), pygame.SRCALPHA)

            # دایره‌های تو در تو با آلفای متغیر، گرادیان نرم از مرکز به لبه ایجاد می‌کنند.
            # Concentric circles with varying alpha create a smooth gradient from the center outward.
            for rr in range(r, 0, -1):
                a = int(80 * (1 - rr / r) ** 1.6)
                pygame.draw.circle(glow, (*self._color_glow, a), (r, r), rr)

            Bullet._glow_cache[key] = glow

        # برای حالت مات، سطح ذخیره‌شده مستقیماً با ترکیب افزایشی رسم می‌شود.
        # For the opaque case, draws the cached surface directly using additive blending.
        if alpha >= 250:
            surface.blit(
                glow, (self.x - r, self.y - r),
                special_flags=pygame.BLEND_RGBA_ADD,
            )
        else:
            # اعمال کاهش شفافیت بدون دست‌زدن به کش
            # با کپی گرفتن از سطح کش‌شده، شفافیت همان گلوله را تغییر می‌دهد بدون اینکه نسخه‌ی اصلی دست‌کاری شود.
            # Copies the cached surface to adjust this bullet's opacity without modifying the original cached version.
            tmp = glow.copy()
            tmp.set_alpha(alpha)
            surface.blit(tmp, (self.x - r, self.y - r),
                         special_flags=pygame.BLEND_RGBA_ADD)

    @staticmethod
    def _draw_line_alpha(
        surface: pygame.Surface,
        color: tuple[int, int, int, int],
        p1: tuple[float, float],
        p2: tuple[float, float],
        width: int,
    ) -> None:
        """رسم خط با شفافیت، چون pygame.draw.line آلفا را نادیده می‌گیرد."""
        # مختصات دو سر خط را به عدد صحیح تبدیل می‌کند تا برای ترسیم پیکسلی آماده باشند.
        # Converts both line endpoints to integers for pixel-based drawing.
        x1, y1 = int(p1[0]), int(p1[1])
        x2, y2 = int(p2[0]), int(p2[1])

        # کوتاه‌ترین مسیر
        # طول تقریبی خط را با بیشترین اختلاف مختصات محاسبه می‌کند و حداقل مقدار یک را در نظر می‌گیرد.
        # Estimates line length using the largest coordinate difference, with a minimum value of one.
        length = max(abs(x2 - x1), abs(y2 - y1), 1)

        # برای خطوط بلند، از رسم ساده‌ی تک‌رنگ استفاده می‌کند تا هزینه‌ی ساخت Surface موقت کاهش یابد.
        # Uses simple solid-color drawing for long lines to reduce the cost of creating temporary surfaces.
        if length > 64:
            # خط خیلی بلند، ساده‌سازی با خط تک‌رنگ
            pygame.draw.line(surface, color[:3], (x1, y1), (x2, y2), width)
            return

        # برای خطوط کوتاه، سطح شفافی با ابعاد متناسب با محدوده‌ی خط ایجاد می‌کند.
        # Creates a transparent surface sized to the line's bounds for short lines.
        tmp = pygame.Surface((abs(x2 - x1) + width * 2 + 2,
                              abs(y2 - y1) + width * 2 + 2), pygame.SRCALPHA)

        # مبدأ سطح موقت را با حاشیه‌ای برابر ضخامت خط تعیین می‌کند.
        # Sets the temporary surface origin with padding equal to the line width.
        ox = min(x1, x2) - width
        oy = min(y1, y2) - width

        # خط را با رنگ چهارکاناله روی سطح شفاف رسم می‌کند و سپس در مختصات اصلی قرار می‌دهد.
        # Draws the four-channel line onto the transparent surface and then places it at the original coordinates.
        pygame.draw.line(
            tmp, color,
            (x1 - ox, y1 - oy),
            (x2 - ox, y2 - oy),
            width,
        )
        surface.blit(tmp, (ox, oy))

    def deals_damage_to(self, entity: Entity) -> bool:
        """آیا این گلوله به موجودیت داده‌شده آسیب می‌زند؟ (بر اساس friendly)"""
        # نوع موجودیت هدف را بر اساس مالکیت گلوله بررسی می‌کند.
        # Checks the target entity type according to the bullet's allegiance.
        if not self.friendly:
            # گلوله‌ی دشمن به پلیر آسیب می‌زند، نه به دشمن‌ها
            from entities.player import Player
            return isinstance(entity, Player)
        else:
            # گلوله‌ی پلیر به دشمن‌ها آسیب می‌زند
            from entities.player import Player
            return not isinstance(entity, Player)

    def consume_hit(self) -> bool:
        """
        پس از برخورد با یک هدف، Pierce را کم می‌کند.
        اگر Pierce تمام شود، گلوله نابود می‌شود و True برمی‌گرداند.
        """
        # اگر مقدار Pierce صفر یا کمتر باشد، گلوله پس از همین برخورد نابود می‌شود.
        # If Pierce is zero or less, the bullet is destroyed after this hit.
        if self.pierce <= 0:
            self.kill()
            return True

        # در غیر این صورت، یک واحد از ظرفیت عبور گلوله کم می‌کند و اجازه‌ی ادامه‌ی حرکت می‌دهد.
        # Otherwise, decreases the bullet's remaining piercing capacity by one and allows it to continue.
        self.pierce -= 1
        return False


class Bomb(Bullet):
    """بمب Bombardier — آروم، درخشان، با فیوز و انفجار."""

    def __init__(self, x, y, vx=0, vy=100, *, scene=None):
        # بمب را با نوع گلوله‌ی دشمن، سرعت ورودی و عمر چهارثانیه‌ای مقداردهی اولیه می‌کند.
        # Initializes the bomb as an enemy bullet with the supplied velocity and a four-second lifetime.
        super().__init__(
            x, y, vx, vy,
            friendly=False,
            kind=BulletKind.ENEMY,
            scene=scene,
            life=4.0,
        )

        # زمان سپری‌شده از عمر بمب و زاویه‌ی چرخش نمایشی آن را نگه می‌دارد.
        # Tracks the bomb's elapsed age and its visual rotation angle.
        self._bomb_age = 0.0
        self._bomb_rotation = 0.0

    def update_entity(self, dt: float) -> None:
        # ابتدا منطق عمومی حرکت، عمر و وضعیت گلوله‌ی پایه را اجرا می‌کند.
        # First runs the base bullet logic for movement, lifetime, and state updates.
        super().update_entity(dt)

        # زمان عمر و مقدار چرخش بمب را در هر فریم افزایش می‌دهد.
        # Increments the bomb's age and rotation value on each frame.
        self._bomb_age += dt
        self._bomb_rotation += dt * 3.0

    def draw_entity(self, surface: pygame.Surface) -> None:
        # ---- محاسبه‌ی alpha (نزدیک انفجار قرمزتر می‌شه) ----
        # میزان نزدیک شدن بمب به زمان انفجار و مقدار پالس نوری آن را محاسبه می‌کند.
        # Calculates how close the bomb is to detonation and determines its visual pulse.
        warn = min(1.0, self._bomb_age / 3.0)
        pulse = 0.5 + 0.5 * math.sin(self._bomb_age * 15)

        # مختصات صحیح مرکز بمب را برای ترسیم اجزای ظاهری به دست می‌آورد.
        # Retrieves the integer center coordinates used to draw the bomb's visual components.
        cx, cy = self.pos_int

        # ---- هاله‌ی نارنجی بزرگ ----
        # شعاع هاله را با توجه به شدت هشدار و پالس نوری تغییر می‌دهد.
        # Varies the glow radius according to the warning level and light pulse.
        glow_r = int(14 + 8 * pulse * warn)

        # با رسم دایره‌های تو در تو، هاله‌ای نارنجی با شدت تدریجی ایجاد می‌کند.
        # Creates an orange glow with gradually changing intensity by drawing concentric circles.
        for rr in range(glow_r, 0, -2):
            a = int(120 * (1 - rr / glow_r) * (0.5 + warn * 0.5))
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 150, 60, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, cy - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # ---- بدنه‌ی بمب (بیضی چرخان) ----
        # شعاع بدنه را برای رسم اجزای مرکزی بمب مشخص می‌کند.
        # Defines the body radius used to draw the bomb's central components.
        body_r = 8

        # سایه
        # دایره‌ی تیره‌ی کمی جابه‌جا شده، سایه‌ی زیر بدنه را ایجاد می‌کند.
        # A slightly offset dark circle creates the shadow beneath the bomb body.
        pygame.draw.circle(surface, (20, 20, 30), (cx + 1, cy + 1), body_r)

        # بدنه
        # سطح اصلی بدنه را با رنگ تیره رسم می‌کند.
        # Draws the main body using a dark fill color.
        pygame.draw.circle(surface, (40, 40, 55), (cx, cy), body_r)

        # حلقه‌ی روشن
        # حاشیه‌ی نارنجی، مرز بدنه‌ی بمب را برجسته می‌کند.
        # The orange outline emphasizes the boundary of the bomb body.
        pygame.draw.circle(surface, (255, 130, 40), (cx, cy), body_r, 2)

        # خط عمودی روی بمب (شکاف)
        # یک شکاف باریک روی بدنه رسم می‌کند تا جزئیات ظاهری بمب کامل شود.
        # Draws a narrow slit on the body to complete the bomb's visual details.
        pygame.draw.line(surface, (255, 200, 100),
                         (cx, cy - body_r + 2), (cx, cy + body_r - 2), 1)

        # ---- فیوز بالای بمب (با جرقه) ----
        # محل انتهای فیوز را بالاتر از بدنه تعیین می‌کند و اتصال آن را رسم می‌کند.
        # Positions the fuse endpoint above the body and draws the connecting line.
        fuse_y = cy - body_r - 4
        pygame.draw.line(surface, (100, 100, 80),
                         (cx, cy - body_r), (cx, fuse_y), 2)

        # جرقه‌ی فیوز (رنگ با پالس)
        # اندازه و رنگ جرقه را با توجه به مقدار پالس تغییر می‌دهد.
        # Varies the spark size and color according to the pulse value.
        spark_r = int(2 + 2 * pulse)
        spark_color = (255, int(180 + 75 * pulse), int(80 + 100 * pulse))

        # دایره‌های شفاف اطراف جرقه، هاله‌ی نورانی آن را ایجاد می‌کنند.
        # Translucent circles around the spark create its glowing effect.
        for rr in range(spark_r * 3, 0, -1):
            a = int(200 * (1 - rr / (spark_r * 3)))
            if a > 0:
                g = pygame.Surface((rr * 4, rr * 4), pygame.SRCALPHA)
                pygame.draw.circle(g, (*spark_color, a), (rr * 2, rr * 2), rr)
                surface.blit(g, (cx - rr * 2, fuse_y - rr * 2),
                             special_flags=pygame.BLEND_RGBA_ADD)

        # هسته‌ی جرقه و نقطه‌ی سفید مرکزی را روی انتهای فیوز رسم می‌کند.
        # Draws the spark core and its central white highlight at the end of the fuse.
        pygame.draw.circle(surface, spark_color, (cx, fuse_y), spark_r)
        pygame.draw.circle(surface, (255, 255, 255), (cx, fuse_y), max(1, spark_r // 2))

        # ---- نشانگر انفجار نزدیک ----
        # پس از عبور هشدار از آستانه، حلقه‌ای قرمز رسم می‌کند که نزدیک شدن انفجار را نشان می‌دهد.
        # Draws a red ring after the warning threshold is reached to indicate an approaching detonation.
        if warn > 0.7:
            progress = (warn - 0.7) / 0.3
            ring_r = int(15 + progress * 10)
            pygame.draw.circle(surface, (255, 80, 40),
                               (cx, cy), ring_r, 2)

    def on_death(self) -> None:
        """انفجار بمب هنگام از بین رفتن."""
        # افکت انفجار فقط در صورت وجود صحنه‌ی بازی ایجاد می‌شود.
        # Creates the explosion effect only when a gameplay scene is available.
        if self.scene is not None:
            try:
                from systems.particles import ParticleKind

                # ذرات انفجار نارنجی
                # مجموعه‌ای از ذرات جرقه با رنگ، سرعت، اندازه و عمر متغیر در محل بمب منتشر می‌کند.
                # Emits spark particles at the bomb's position with varying colors, speeds, sizes, and lifetimes.
                self.scene.particles.emit_burst(
                    self.x, self.y,
                    count=18,
                    color_start=(255, 240, 180),
                    color_end=(255, 60, 20),
                    speed_min=100, speed_max=320,
                    life_min=0.3, life_max=0.7,
                    size_min=2, size_max=5,
                    kind=ParticleKind.SPARK,
                    additive=True,
                )

                # حلقه‌ی انفجار
                # یک حلقه‌ی ذره‌ای پیرامون نقطه‌ی انفجار ایجاد می‌کند تا گسترش موج انفجار نمایش داده شود.
                # Creates a particle ring around the explosion point to visualize the expanding shockwave.
                self.scene.particles.emit_ring(
                    self.x, self.y,
                    count=14, radius=6, speed=240,
                    color=(255, 180, 80), life=0.4, size=2,
                )
            except Exception:
                # خطای تولید ذرات نباید مانع نابودی بمب شود.
                # Prevents a particle-generation error from interrupting the bomb's destruction.
                pass


__all__ = ["Bullet", "BulletKind", "Bomb"]
"""
systems/camera.py
=================

سیستم دوربین (Camera) برای SPACE BLASTER.

این ماژول حس «سینمایی» بازی را می‌سازد. دوربین در این بازی نیازی به
دنبال کردن پلیر ندارد (پلیر همیشه در کادر است)، اما از سه ویژگی
مهم پشتیبانی می‌کند که تفاوت بین یک بازی معمولی و یک بازی AAA را
می‌سازد:

      Screen Shake — لرزش صفحه هنگام انفجار، برخورد، شلیک سنگین
      Zoom — کوچک و بزرگ شدن سینمایی (برای باس‌ها یا لحظات دراماتیک)
      Offset — جابه‌جایی ملایم دوربین (برای recoil یا افکت‌های خاص)

ویژگی‌های کلیدی:
    • لرزش با decay نمایی — نه خطی، چون خطی مصنوعی به نظر می‌رسد
    • پشتیبانی از لرزش جهت‌دار (directional shake) با falloff
    • Traum-based shake — روش استاندارد صنعت (Squirrel Eiserloh)
    • Zoom نرم با میان‌یابی خطی
    • پس‌لرزه (aftershock) اختیاری برای انفجارهای بزرگ
    • ذخیره‌ی offset فعلی برای استفاده در رندر
    • غیرفعال‌سازی موقت (برای منوی Pause یا صحنه‌های آرام)
    • سازگار با هر رزولوشن و هر FPS (بدون وابستگی به فریم)

استفاده:
    cam = Camera()
    cam.shake(12.0)          # لرزش عمومی
    cam.shake(20.0, dir=(1,0))  # لرزش افقی
    cam.set_zoom(1.05, 0.4)  # زوم ۵٪ در ۰.۴ ثانیه
    cam.update(dt)
    ox, oy = cam.offset
    surface.blit(world, (ox, oy))
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from core import settings as S



class Camera:
    """
    دوربین بازی با Screen Shake و Zoom.

    مدل لرزش بر پایه‌ی «Trauma» است: یک مقدار 0..1 که با هر ضربه
    افزایش می‌یابد و به‌صورت نمایی کاهش می‌یابد. شدت جابه‌جایی =
    trauma² × max_offset، که باعث می‌شود کاهش لرزش طبیعی‌تر حس شود.

    پارامترها:
        max_offset    — حداکثر جابه‌جایی دوربین در پیکسل
        max_rotation  — حداکثر چرخش دوربین در درجه
        decay         — ضریب کاهش trauma در هر ثانیه
        trauma_scale  — ضریب تبدیل «شدت ورودی» به trauma
    """

    def __init__(
        self,
        *,
        max_offset: float = 22.0,
        max_rotation: float = 1.4,
        decay: float = 1.8,
        trauma_scale: float = 0.014,
    ) -> None:
        # ---- تنظیمات ----
        # مقادیر ورودی، دامنه‌ی جابه‌جایی، چرخش، کاهش لرزش و مقیاس شدت ضربه را تعیین می‌کنند.
        # Input values define the offset range, rotation, shake decay, and impact-strength scale.
        self.max_offset: float = float(max_offset)
        self.max_rotation: float = float(max_rotation)
        self.decay: float = float(decay)
        self.trauma_scale: float = float(trauma_scale)

        # ---- وضعیت ----
        # وضعیت فعلی لرزش، جابه‌جایی و چرخش دوربین در این متغیرها نگهداری می‌شود.
        # The camera's current shake, offset, and rotation state are stored in these variables.
        self._trauma: float = 0.0
        self._offset: tuple[float, float] = (0.0, 0.0)
        self._rotation: float = 0.0

        # ---- Zoom ----
        # مقدار زوم فعلی به‌تدریج به مقدار هدف نزدیک می‌شود.
        # The current zoom value gradually approaches its target value.
        self._zoom: float = 1.0
        self._zoom_target: float = 1.0
        self._zoom_speed: float = 1.0     # ضریب lerp در ثانیه

        # ---- لرزش جهت‌دار ----
        # مؤلفه‌های افقی و عمودی لرزش جهت‌دار مستقل از لرزش نویزی نگهداری می‌شوند.
        # Horizontal and vertical components of directional shake are maintained independently of noise-based shake.
        self._dir_shake_x: float = 0.0
        self._dir_shake_y: float = 0.0
        self._dir_decay: float = 5.0

        # ---- پس‌لرزه ----
        # شمارنده، زمان‌بندی و شدت پس‌لرزه‌ها برای ایجاد ضربه‌های کوچک بعد از لرزش اصلی استفاده می‌شوند.
        # The aftershock count, timing, and strength produce smaller impacts after the main shake.
        self._aftershock_count: int = 0
        self._aftershock_timer: float = 0.0
        self._aftershock_interval: float = 0.12
        self._aftershock_strength: float = 0.0

        # ---- کنترل ----
        # زمان و seedهای مستقل، الگوی نویز دوربین را در طول اجرا تغییر می‌دهند.
        # Time and independent seeds vary the camera's noise pattern throughout execution.
        self.enabled: bool = True
        self._t: float = 0.0
        self._noise_seed_x: float = random.uniform(0, 1000)
        self._noise_seed_y: float = random.uniform(0, 1000)


    @property
    def offset(self) -> tuple[float, float]:
        """
        جابه‌جایی فعلی دوربین (به پیکسل).
        برای رندر، این را به موقعیت دنیا اضافه کن:
            surface.blit(world_surface, self.camera.offset)
        """
        return self._offset

    @property
    def rotation(self) -> float:
        """چرخش فعلی دوربین (درجه). برای رندر پیشرفته."""
        return self._rotation

    @property
    def trauma(self) -> float:
        """سطح trauma فعلی (0..1)."""
        return self._trauma

    @property
    def zoom(self) -> float:
        """ضریب زوم فعلی (1.0 = بدون زوم)."""
        return self._zoom

    @property
    def is_shaking(self) -> bool:
        # وجود trauma یا باقی‌ماندن هرکدام از مؤلفه‌های لرزش جهت‌دار، فعال بودن لرزش را نشان می‌دهد.
        # Nonzero trauma or either remaining directional-shake component indicates that the camera is shaking.
        return self._trauma > 0.01 or abs(self._dir_shake_x) > 0.01 or abs(self._dir_shake_y) > 0.01


    def shake(
        self,
        strength: float,
        *,
        direction: Optional[tuple[float, float]] = None,
        aftershock: int = 0,
    ) -> None:
        """
        اعمال لرزش به دوربین.

        پارامترها:
            strength    — شدت (پیشنهاد: 3 ملایم، 12 متوسط، 25 شدید)
            direction   — اگر داده شود، لرزش در این جهت biased می‌شود
                          (برای انفجارهای جانبی، recoil اسلحه)
            aftershock  — تعداد پس‌لرزه‌های کوچک بعد از لرزش اصلی

        مثال:
            cam.shake(12.0)                 # لرزش معمولی
            cam.shake(18.0, direction=(1,0)) # لرزش به راست
            cam.shake(30.0, aftershock=3)   # انفجار بزرگ با پس‌لرزه
        """
        # در صورت غیرفعال بودن دوربین، درخواست لرزش بدون تغییر وضعیت نادیده گرفته می‌شود.
        # When the camera is disabled, shake requests are ignored without changing its state.
        if not self.enabled:
            return

        # تبدیل strength به trauma (جمع‌شونده)
        # شدت ورودی با مقیاس مشخص به trauma تبدیل و به مقدار قبلی اضافه می‌شود؛ سقف آن یک است.
        # Input strength is scaled into trauma and added to the previous value, with a maximum of one.
        add = strength * self.trauma_scale
        self._trauma = min(1.0, self._trauma + add)

        # لرزش جهت‌دار
        if direction is not None:
            # بردار ورودی نرمال می‌شود تا جهت حفظ شود و شدت مستقل از طول بردار باقی بماند.
            # The input vector is normalized to preserve its direction while keeping strength independent of vector length.
            dx, dy = direction
            d = math.hypot(dx, dy) or 1.0
            ux, uy = dx / d, dy / d
            mag = strength * 0.4
            self._dir_shake_x += ux * mag
            self._dir_shake_y += uy * mag

        # پس‌لرزه
        if aftershock > 0:
            # درخواست جدید تعداد پس‌لرزه‌ها را کمتر نمی‌کند و زمان و شدت آن‌ها را بازتنظیم می‌کند.
            # A new request never reduces the pending aftershock count and resets its timing and strength.
            self._aftershock_count = max(self._aftershock_count, aftershock)
            self._aftershock_timer = self._aftershock_interval
            self._aftershock_strength = strength * 0.35

    def set_zoom(self, target: float, duration: float = 0.4) -> None:
        """
        تنظیم زوم هدف با سرعت مشخص.
        duration = زمان تقریبی رسیدن به هدف (ثانیه).
        """
        # مقدار هدف حداقل ۰.۱ است تا از زوم صفر یا مقادیر منفی جلوگیری شود.
        # The target is clamped to at least 0.1 to prevent zero or negative zoom values.
        self._zoom_target = max(0.1, float(target))
        if duration <= 0.0:
            # در مدت صفر یا منفی، زوم بدون انیمیشن مستقیماً به هدف می‌رسد.
            # With a zero or negative duration, zoom reaches its target immediately without animation.
            self._zoom = self._zoom_target
            self._zoom_speed = 9999.0
        else:
            # تخمین ضریب lerp
            # سرعت میان‌یابی بر اساس مدت درخواستی تنظیم می‌شود تا زوم تقریباً در همان بازه به هدف برسد.
            # The interpolation speed is derived from the requested duration so zoom reaches its target approximately within that interval.
            self._zoom_speed = max(0.1, 4.0 / duration)

    def punch_zoom(self, amount: float = 0.08, *, restore: float = 0.5) -> None:
        """
        یک ضربه‌ی زوم سریع + بازگشت نرم.
        برای بازخورد قوی (شلیک سنگین، باس، …)
        """
        # زوم ابتدا فوراً افزایش می‌یابد و سپس با سرعت تعیین‌شده به مقدار عادی بازمی‌گردد.
        # Zoom increases immediately, then smoothly returns to its normal value at the configured speed.
        self._zoom = 1.0 + amount
        self._zoom_target = 1.0
        self._zoom_speed = max(0.1, 4.0 / max(0.05, restore))

    def reset(self) -> None:
        """بازنشانی کامل دوربین به حالت عادی."""
        # تمام وضعیت‌های موقت دوربین پاک می‌شوند تا هیچ اثر باقی‌مانده‌ای به فریم‌های بعد منتقل نشود.
        # All temporary camera states are cleared so no residual effects carry over to subsequent frames.
        self._trauma = 0.0
        self._offset = (0.0, 0.0)
        self._rotation = 0.0
        self._zoom = 1.0
        self._zoom_target = 1.0
        self._dir_shake_x = 0.0
        self._dir_shake_y = 0.0
        self._aftershock_count = 0
        self._aftershock_timer = 0.0
        self._aftershock_strength = 0.0


    def update(self, dt: float) -> None:
        """
        به‌روزرسانی وضعیت دوربین. این متد را در ابتدای هر فریم
        (قبل از رندر) صدا بزن.
        """
        if not self.enabled:
            # در حالت غیرفعال، جابه‌جایی و چرخش صفر می‌شوند و به‌روزرسانی سایر افکت‌ها متوقف می‌شود.
            # When disabled, offset and rotation are zeroed and updates to the other effects are suspended.
            self._offset = (0.0, 0.0)
            self._rotation = 0.0
            return

        self._t += dt

        # ---- کاهش trauma (نمایی) ----
        # کاهش trauma بر اساس زمان سپری‌شده انجام می‌شود، نه تعداد فریم‌ها.
        # Trauma decay is based on elapsed time rather than the number of frames.
        if self._trauma > 0.0:
            self._trauma = max(0.0, self._trauma - self.decay * dt)

        # ---- پس‌لرزه ----
        self._update_aftershock(dt)

        # ---- کاهش لرزش جهت‌دار ----
        # هر دو مؤلفه با ضریب وابسته به dt تضعیف می‌شوند تا لرزش جهت‌دار به‌تدریج محو شود.
        # Both components are damped by a dt-dependent factor so directional shake gradually fades.
        if self._dir_shake_x != 0.0 or self._dir_shake_y != 0.0:
            damp = max(0.0, 1.0 - self._dir_decay * dt)
            self._dir_shake_x *= damp
            self._dir_shake_y *= damp
            if abs(self._dir_shake_x) < 0.05:
                self._dir_shake_x = 0.0
            if abs(self._dir_shake_y) < 0.05:
                self._dir_shake_y = 0.0

        # ---- Zoom نرم ----
        # میان‌یابی با ضریب محدودشده، زوم را در هر فریم به مقدار هدف نزدیک می‌کند.
        # Clamped interpolation moves the current zoom toward its target on each frame.
        if abs(self._zoom - self._zoom_target) > 1e-4:
            blend = min(1.0, dt * self._zoom_speed)
            self._zoom += (self._zoom_target - self._zoom) * blend
        else:
            self._zoom = self._zoom_target

        # ---- محاسبه‌ی offset نهایی ----
        self._compute_offset()

    def _update_aftershock(self, dt: float) -> None:
        """پس‌لرزه‌ها را زمان‌بندی و اعمال می‌کند."""
        if self._aftershock_count <= 0:
            return

        # زمان باقی‌مانده کاهش می‌یابد و با رسیدن به صفر، یک پس‌لرزه اعمال می‌شود.
        # The remaining timer decreases, and one aftershock is triggered when it reaches zero.
        self._aftershock_timer -= dt
        if self._aftershock_timer <= 0.0:
            self._aftershock_count -= 1
            self._aftershock_timer = self._aftershock_interval
            # پس‌لرزه‌ی کوچک — با noise بهتر حس می‌شود
            # هر پس‌لرزه مقدار محدودی trauma اضافه می‌کند و شدت کلی همچنان در سقف یک باقی می‌ماند.
            # Each aftershock adds a limited amount of trauma while keeping the overall intensity capped at one.
            self._trauma = min(1.0, self._trauma + self._aftershock_strength * self.trauma_scale)


    def _compute_offset(self) -> None:
        """
        offset نهایی = shake (نویز تصادفی) + dir_shake + rotation
        """
        # ---- component 1: noise-based random shake ----
        # از ترکیب چند سینوس با فرکانس‌های متفاوت استفاده می‌کنیم تا
        # لرزش حس ارگانیک داشته باشد (نه فقط random.random خالص).
        # ترکیب نویز هموار و تغییرات تصادفی، لرزشی کمتر تکراری و طبیعی‌تر ایجاد می‌کند.
        # Combining smooth noise with random variation produces less repetitive and more natural-looking shake.
        intensity = self._trauma * self._trauma   # مربع — کاهش طبیعی
        amp = self.max_offset * intensity

        if amp > 0.01:
            # نویز نرم بر پایه‌ی زمان
            # سینوس‌ها حرکت پیوسته ایجاد می‌کنند و مؤلفه‌ی تصادفی، تغییرات نامنظم کوچکی به آن اضافه می‌کند.
            # The sine waves create continuous movement, while the random component adds small irregular variations.
            t = self._t * 30.0
            nx = (
                math.sin(t * 1.17 + self._noise_seed_x) * 0.5
                + math.sin(t * 2.31 + self._noise_seed_x * 0.7) * 0.3
                + random.uniform(-0.4, 0.4) * 0.5
            )
            ny = (
                math.sin(t * 1.53 + self._noise_seed_y) * 0.5
                + math.sin(t * 2.79 + self._noise_seed_y * 0.9) * 0.3
                + random.uniform(-0.4, 0.4) * 0.5
            )
            shake_x = nx * amp
            shake_y = ny * amp
        else:
            # وقتی شدت مؤثر ناچیز است، مؤلفه‌ی نویزی صفر می‌شود تا لرزش جزئی باقی نماند.
            # When the effective intensity is negligible, the noise components are zeroed to avoid residual movement.
            shake_x = 0.0
            shake_y = 0.0

        # ---- component 2: directional shake ----
        dir_x = self._dir_shake_x
        dir_y = self._dir_shake_y

        # ---- ترکیب ----
        # لرزش نویزی و جهت‌دار با هم جمع می‌شوند تا offset نهایی هر محور به دست آید.
        # Noise-based and directional shake are added together to produce the final offset on each axis.
        total_x = shake_x + dir_x
        total_y = shake_y + dir_y

        # ---- rotation (چرخش ملایم، تابع trauma) ----
        # چرخش نیز با مربع trauma مقیاس می‌شود تا با کاهش شدت لرزش، نرم‌تر محو شود.
        # Rotation is also scaled by squared trauma so it fades smoothly as shake intensity decreases.
        if intensity > 0.01:
            rot = math.sin(self._t * 26.0 + self._noise_seed_y) * self.max_rotation * intensity
        else:
            rot = 0.0

        # ---- اعمال zoom روی shake (زوم بیشتر = shake نسبی کمتر) ----
        # (پیش‌فرض: بدون تغییر)

        self._offset = (total_x, total_y)
        self._rotation = rot


    def apply_to_surface(
        self,
        world: "pygame.Surface",  # type: ignore[name-defined]
        screen: "pygame.Surface",  # type: ignore[name-defined]
    ) -> None:
        """
        سطح دنیا را با در نظر گرفتن offset و zoom روی صفحه می‌کشد.
        اگر فقط می‌خواهی offset را دستی اعمال کنی، از self.offset استفاده کن.

        نکته: این متد برای سازگاری ارائه شده؛ در GameplayScene می‌توانی
        منطق دلخواه خودت را داشته باشی.
        """
        import pygame  # import محلی برای جلوگیری از وابستگی سراسری

        ox, oy = self._offset

        if abs(self._zoom - 1.0) < 1e-3:
            # بدون zoom — رسم سریع
            # وقتی زوم تقریباً برابر یک است، از تغییر اندازه‌ی سطح صرف‌نظر می‌شود و رندر مستقیم انجام می‌گیرد.
            # When zoom is approximately one, scaling is skipped and the surface is rendered directly.
            screen.blit(world, (ox, oy))
            return

        # با zoom — scale و رسم وسط‌چین
        # ابعاد سطح با ضریب زوم محاسبه و تصویر با حفظ مرکز صفحه در اندازه‌ی جدید رسم می‌شود.
        # The surface dimensions are scaled, then the image is drawn at the new size while keeping the screen center fixed.
        w, h = world.get_size()
        scaled_w = int(w * self._zoom)
        scaled_h = int(h * self._zoom)
        scaled = pygame.transform.smoothscale(world, (scaled_w, scaled_h))
        # وسط‌چین کردن نسبت به صفحه
        # offset دوربین پس از محاسبه‌ی موقعیت مرکزی به مختصات نهایی اضافه می‌شود.
        # The camera offset is added to the centered position to obtain the final drawing coordinates.
        cx = (screen.get_width() - scaled_w) // 2 + int(ox)
        cy = (screen.get_height() - scaled_h) // 2 + int(oy)
        screen.blit(scaled, (cx, cy))


    def world_to_screen(
        self,
        wx: float, wy: float,
        screen_w: int, screen_h: int,
    ) -> tuple[float, float]:
        """
        تبدیل مختصات دنیا به مختصات صفحه با در نظر گرفتن offset و zoom.
        برای مواقعی که می‌خواهی یک HUD شناور یا نشانگر روی یه موقعیت دنیا
        بذاری.
        """
        ox, oy = self._offset
        if abs(self._zoom - 1.0) < 1e-3:
            # در حالت بدون زوم، فقط offset دوربین به مختصات دنیا اضافه می‌شود.
            # Without zoom, only the camera offset is added to the world coordinates.
            return (wx + ox, wy + oy)

        # با zoom: نقطه‌ی مرکز صفحه مبناست
        # مختصات نسبت به مرکز صفحه مقیاس می‌شوند تا زوم حول مرکز تصویر انجام شود، نه مبدأ مختصات.
        # Coordinates are scaled relative to the screen center so zoom is applied around the image center rather than the origin.
        cx = screen_w / 2
        cy = screen_h / 2
        sx = cx + (wx - cx) * self._zoom + ox
        sy = cy + (wy - cy) * self._zoom + oy
        return (sx, sy)

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False
        self.reset()


__all__ = ["Camera"]
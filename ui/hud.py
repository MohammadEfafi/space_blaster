"""
ui/hud.py
=========

رابط کاربری درون‌بازی (HUD) برای SPACE BLASTER.

این ماژول تمام عناصر نمایشی روی صفحه را مدیریت می‌کند:

    • امتیاز (Score) با شمارنده‌ی نرم که به مقدار هدف میل می‌کند
    • شماره‌ی موج (Wave) با انیمیشن تغییر
    • جان‌ها (HP Hearts) با انیمیشن ترکیدن هنگام از دست دادن
    • نوار Power-Up با تایمر و رنگ‌بندی پویا
    • Combo Counter که با کشتن پی‌درپی دشمن‌ها بالا می‌رود
    • FPS در حالت دیباگ
    • پیام‌های شناور (Floating Texts) برای امتیاز و برداشت پاورآپ

طراحی:
    HUD کاملاً مستقل از منطق بازی است. فقط متدهای set_* و notify_*
    را صدا می‌زنی و HUD بقیه‌ی کارها را می‌کند. انیمیشن‌ها با dt
    کار می‌کنند، پس روی هر FPS یکسان عمل می‌کنند.

استفاده:
    hud = HUD()
    hud.set_score(1250)
    hud.set_hp(3, 3)
    hud.set_wave(2)
    hud.set_powerup(0.65)   # نسبت باقی‌مانده
    hud.notify_score(50, x=400, y=300)
    hud.update(dt)
    hud.draw(surface)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

import pygame

from core import settings as S



@dataclass
class _FloatingText:
    """یک متن شناور که به بالا حرکت می‌کند و محو می‌شود."""
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    life: float
    max_life: float
    vy: float = -55.0
    font_size: int = S.FontCfg.NORMAL
    scale: float = 1.0
    scale_vel: float = 0.0


@dataclass
class _HeartState:
    """وضعیت هر قلب برای انیمیشن."""
    filled: bool = True
    burst_t: float = 0.0    # 0..1، وقتی از دست می‌رود به 1 می‌رسد
    pop_t: float = 0.0      # 0..1، وقتی پر می‌شود پاپ می‌کند



class HUD:
    """
    HUD بازی با انیمیشن‌های نرم.

    پارامترها:
        scene  — رفرنس اختیاری به GameplayScene (برای دسترسی به دوربین و …)
    """

    # ---- تنظیمات ظاهری ----
    PADDING = 14
    BAR_WIDTH = 180
    BAR_HEIGHT = 8

    def __init__(self) -> None:
        # ---- فونت‌ها (lazy-built) ----
        # فونت‌ها فقط هنگام اولین درخواست ساخته می‌شوند و سپس برای استفاده‌ی مجدد ذخیره می‌شوند.
        # Fonts are created only when first requested and then cached for reuse.
        self._font_cache: dict[int, pygame.font.Font] = {}
        self._font_bold_cache: dict[int, pygame.font.Font] = {}

        # ---- مقادیر منطقی ----
        self.score: int = 0
        self.score_display: float = 0.0    # مقدار در حال نمایش (نرم)
        self.high_score: int = 0

        self.hp: int = 0
        self.max_hp: int = 0
        self._hearts: list[_HeartState] = []

        self.wave: int = 0
        self.wave_display_scale: float = 1.0
        self.wave_change_flash: float = 0.0

        self.powerup_ratio: float = 0.0
        self.powerup_color: tuple[int, int, int] = S.Palette.POWERUP_CORE

        # ---- Combo ----
        self.combo: int = 0
        self.combo_timer: float = 0.0
        self.combo_max_time: float = 2.5
        self.combo_scale: float = 1.0

        # ---- متن‌های شناور ----
        self.floaters: list[_FloatingText] = []

        # ---- FPS (دیباگ) ----
        self.fps: float = 0.0
        self._show_fps: bool = S.Debug.SHOW_FPS

        # ---- افکت کلی ----
        self._t: float = 0.0
        self._damage_flash: float = 0.0    # فلاش قرمز صفحه هنگام ضربه

        # ---- HUD مخفی برای صحنه‌های خاص ----
        self.visible: bool = True


    def _get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        # برای فونت معمولی و ضخیم، کش جداگانه نگهداری می‌شود تا تنظیمات آن‌ها با هم تداخل نکند.
        # Separate caches are maintained for regular and bold fonts to keep their configurations independent.
        cache = self._font_bold_cache if bold else self._font_cache
        font = cache.get(size)

        # در صورت نبود فونت در کش، آن را می‌سازد و برای درخواست‌های بعدی ذخیره می‌کند.
        # Creates and caches the font when it is not already available.
        if font is None:
            font = pygame.font.SysFont(S.FontCfg.FAMILY, size, bold=bold)
            cache[size] = font
        return font


    def set_score(self, value: int) -> None:
        """تنظیم امتیاز. نمایش به‌صورت نرم به این مقدار میل می‌کند."""
        self.score = int(value)

    def add_score(self, delta: int) -> None:
        self.score += int(delta)

    def set_high_score(self, value: int) -> None:
        self.high_score = int(value)

    def set_hp(self, hp: int, max_hp: Optional[int] = None) -> None:
        """
        تنظیم جان. اگر max_hp داده شود، تعداد قلب‌ها هم به‌روز می‌شود.
        قلب‌های از دست رفته انیمیشن ترکیدن می‌گیرند.
        """
        # در صورت تغییر ظرفیت جان، ساختار قلب‌ها از ابتدا با وضعیت پر ساخته می‌شود.
        # Rebuilds the heart states as filled whenever the maximum health capacity changes.
        if max_hp is not None and max_hp != self.max_hp:
            self.max_hp = max_hp
            self._hearts = [_HeartState(filled=True) for _ in range(max_hp)]

        old_hp = self.hp
        self.hp = max(0, int(hp))

        # اگر قلب از دست رفت → انیمیشن ترکیدن
        # Lost hearts trigger a burst animation.
        if self.hp < old_hp and self.hp < len(self._hearts):
            # فقط قلب‌هایی که در بازه‌ی جان‌های ازدست‌رفته قرار دارند، وارد انیمیشن ترکیدن می‌شوند.
            # Only hearts within the range of lost health enter the burst animation.
            for i in range(self.hp, min(old_hp, len(self._hearts))):
                self._hearts[i].filled = False
                self._hearts[i].burst_t = 0.0001
            self._damage_flash = 0.6

        # اگر قلب اضافه شد → پاپ
        # Restored hearts trigger a pop animation.
        elif self.hp > old_hp:
            for i in range(old_hp, min(self.hp, len(self._hearts))):
                self._hearts[i].filled = True
                self._hearts[i].pop_t = 0.0001

    def set_wave(self, wave: int) -> None:
        # فقط هنگام تغییر شماره‌ی موج، افکت بزرگ‌شدن و فلاش فعال می‌شود.
        # The scale and flash effects are triggered only when the wave number changes.
        if wave != self.wave:
            self.wave = int(wave)
            self.wave_display_scale = 1.5
            self.wave_change_flash = 0.6

    def set_powerup(self, ratio: float, color: Optional[tuple[int, int, int]] = None) -> None:
        """نسبت باقی‌مانده‌ی پاورآپ (0..1) و رنگ (اختیاری)."""
        # مقدار نسبت به بازه‌ی معتبر محدود می‌شود تا از خارج شدن نوار از محدوده جلوگیری شود.
        # Clamps the ratio to its valid range to prevent the bar from exceeding its bounds.
        self.powerup_ratio = max(0.0, min(1.0, ratio))
        if color is not None:
            self.powerup_color = color

    def set_fps(self, fps: float) -> None:
        self.fps = fps

    def set_show_fps(self, show: bool) -> None:
        self._show_fps = show


    def register_kill(self, combo_value: int = 1) -> None:
        """هر بار دشمن کشته شد، Combo را افزایش می‌ده."""
        # هر کشتن مقدار Combo را افزایش می‌دهد و مهلت ادامه‌ی زنجیره را از نو تنظیم می‌کند.
        # Each kill increases the combo and resets the time window for continuing the chain.
        self.combo += combo_value
        self.combo_timer = self.combo_max_time
        self.combo_scale = 1.4

    def reset_combo(self) -> None:
        self.combo = 0
        self.combo_timer = 0.0


    def notify_score(
        self,
        amount: int,
        x: float, y: float,
        *,
        color: Optional[tuple[int, int, int]] = None,
        prefix: str = "+",
    ) -> None:
        """نمایش «+۵۰» روی موقعیت مشخص."""
        # متن امتیاز با عمر محدود، حرکت رو به بالا و کوچک‌شدن تدریجی ایجاد می‌شود.
        # Creates a score popup with a limited lifetime, upward movement, and gradual shrinking.
        col = color if color else S.Palette.HUD_ACCENT
        self.floaters.append(_FloatingText(
            text=f"{prefix}{amount}",
            x=x, y=y,
            color=col,
            life=0.9, max_life=0.9,
            vy=-60.0,
            font_size=S.FontCfg.NORMAL,
            scale=1.4, scale_vel=-3.0,
        ))

    def notify_text(
        self,
        text: str,
        x: float, y: float,
        *,
        color: Optional[tuple[int, int, int]] = None,
        font_size: int = S.FontCfg.NORMAL,
        life: float = 1.0,
    ) -> None:
        """متن شناور عمومی (مثلاً «WAVE BONUS», «SHIELD»)."""
        # متن عمومی با رنگ، اندازه و مدت نمایش قابل تنظیم به فهرست پیام‌های شناور اضافه می‌شود.
        # Adds a general floating message with configurable color, size, and display duration.
        col = color if color else S.Palette.WHITE
        self.floaters.append(_FloatingText(
            text=text,
            x=x, y=y,
            color=col,
            life=life, max_life=life,
            vy=-70.0,
            font_size=font_size,
            scale=1.2, scale_vel=-2.0,
        ))


    def update(self, dt: float) -> None:
        self._t += dt

        # ---- امتیاز نرم ----
        # اختلاف امتیاز فعلی و مقدار نمایشی برای حرکت تدریجی شمارنده محاسبه می‌شود.
        # Calculates the difference between the actual score and displayed value for gradual counter animation.
        diff = self.score - self.score_display
        if abs(diff) < 0.5:
            self.score_display = float(self.score)
        else:
            # میل نمایی — سریع در ابتدا، آرام در انتها
            # Exponential easing — fast initially and slower as it approaches the target.
            self.score_display += diff * min(1.0, dt * 8.0)

        # ---- فلاش موج ----
        # شدت فلاش و مقیاس اضافه‌شده به شماره‌ی موج به‌مرور به حالت عادی بازمی‌گردند.
        # Gradually returns the wave flash and enlarged display scale to their normal values.
        if self.wave_change_flash > 0.0:
            self.wave_change_flash = max(0.0, self.wave_change_flash - dt * 2.0)
        if self.wave_display_scale > 1.0:
            self.wave_display_scale = max(1.0, self.wave_display_scale - dt * 2.0)

        # ---- Combo ----
        # با پایان مهلت Combo، زنجیره‌ی کشتن دشمن‌ها از صفر شروع می‌شود.
        # Resets the kill chain when the combo time window expires.
        if self.combo_timer > 0.0:
            self.combo_timer -= dt
            if self.combo_timer <= 0.0:
                self.combo = 0
        if self.combo_scale > 1.0:
            self.combo_scale = max(1.0, self.combo_scale - dt * 4.0)

        # ---- فلاش قرمز ضربه ----
        # شدت فلاش آسیب به‌تدریج کاهش می‌یابد و در صفر متوقف می‌شود.
        # Gradually reduces the damage flash intensity until it reaches zero.
        if self._damage_flash > 0.0:
            self._damage_flash = max(0.0, self._damage_flash - dt * 1.5)

        # ---- قلب‌ها ----
        # زمان‌بندی انیمیشن ترکیدن و ظاهرشدن هر قلب به‌صورت مستقل پیش می‌رود.
        # Advances each heart's burst and pop animation independently.
        for h in self._hearts:
            if h.burst_t > 0.0 and h.burst_t < 1.0:
                h.burst_t = min(1.0, h.burst_t + dt * 3.5)
            if h.pop_t > 0.0 and h.pop_t < 1.0:
                h.pop_t = min(1.0, h.pop_t + dt * 4.0)

        # ---- متن‌های شناور ----
        # فهرست جدید فقط شامل پیام‌هایی خواهد بود که هنوز زمان نمایش دارند.
        # Builds a new list containing only messages that still have display time remaining.
        alive_floaters: list[_FloatingText] = []
        for f in self.floaters:
            f.life -= dt
            if f.life <= 0.0:
                continue

            # موقعیت عمودی با سرعت فعلی تغییر می‌کند و سرعت نیز به‌تدریج کاهش می‌یابد.
            # Updates the vertical position using the current velocity and gradually reduces that velocity.
            f.y += f.vy * dt
            f.vy *= (1.0 - dt * 2.2)

            # مقیاس متن تا رسیدن به اندازه‌ی عادی تغییر می‌کند و سپس انیمیشن متوقف می‌شود.
            # Adjusts the text scale until it reaches its normal size, then stops the scaling animation.
            if f.scale_vel != 0.0:
                f.scale += f.scale_vel * dt
                if f.scale < 1.0:
                    f.scale = 1.0
                    f.scale_vel = 0.0
            alive_floaters.append(f)
        self.floaters = alive_floaters


    def draw(self, surface: pygame.Surface) -> None:
        # در حالت مخفی، رسم تمام اجزای HUD متوقف می‌شود.
        # Skips drawing all HUD elements when visibility is disabled.
        if not self.visible:
            return

        # ترتیب فراخوانی، ترتیب لایه‌های نمایشی HUD را مشخص می‌کند.
        # The call order determines the rendering order of the HUD layers.
        self._draw_damage_vignette(surface)
        self._draw_score(surface)
        self._draw_wave(surface)
        self._draw_hearts(surface)
        self._draw_powerup(surface)
        self._draw_combo(surface)
        self._draw_floaters(surface)
        if self._show_fps:
            self._draw_fps(surface)

    # ── وینیت قرمز هنگام ضربه ──
    def _draw_damage_vignette(self, surface: pygame.Surface) -> None:
        if self._damage_flash <= 0.01:
            return

        # شدت افکت به مقدار فلاش وابسته است و ابعاد سطح مقصد برای ساخت لایه‌ی پوشاننده استفاده می‌شود.
        # The effect intensity depends on the flash value, while the target surface dimensions define the overlay.
        a = int(140 * self._damage_flash)
        w, h = surface.get_size()
        # از گوشه‌ها به مرکز — گرادیان شعاعی ساده با چند لایه
        # From the edges toward the center — a simple radial gradient built from multiple layers.
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        thickness = 80
        for i in range(thickness):
            # با افزایش فاصله از لبه، آلفا کاهش پیدا می‌کند تا مرکز صفحه شفاف‌تر بماند.
            # Alpha decreases with distance from the edges, leaving the screen center more transparent.
            alpha = int(a * (1 - i / thickness))
            if alpha <= 0:
                continue
            color = (*S.Palette.HUD_HP, alpha)
            # لبه‌ی چپ
            pygame.draw.line(overlay, color, (i, 0), (i, h))
            # لبه‌ی راست
            pygame.draw.line(overlay, color, (w - 1 - i, 0), (w - 1 - i, h))
            # بالا
            pygame.draw.line(overlay, color, (0, i), (w, i))
            # پایین
            pygame.draw.line(overlay, color, (0, h - 1 - i), (w, h - 1 - i))
        surface.blit(overlay, (0, 0))

    # ── امتیاز ──
    def _draw_score(self, surface: pygame.Surface) -> None:
        x = self.PADDING
        y = self.PADDING

        # برچسب کوچک
        # Small label
        label = self._get_font(S.FontCfg.SMALL, bold=True)
        img_label = label.render("SCORE", True, S.Palette.HUD_ACCENT)
        surface.blit(img_label, (x, y))

        # مقدار
        # Score value
        # مقدار نمایشی به عدد صحیح و قالب جداکننده‌ی هزارگان تبدیل می‌شود.
        # Converts the displayed value to an integer with thousands separators.
        font = self._get_font(S.FontCfg.LARGE, bold=True)
        text = f"{int(self.score_display):,}"
        img = font.render(text, True, S.Palette.WHITE)
        surface.blit(img, (x, y + img_label.get_height() + 2))

        # High Score (زیر امتیاز جاری)
        # High Score (below the current score)
        if self.high_score > 0:
            hs_font = self._get_font(S.FontCfg.TINY)
            hs_text = f"BEST {self.high_score:,}"
            img_hs = hs_font.render(hs_text, True, S.Palette.GREY)
            surface.blit(img_hs, (x, y + img_label.get_height() + img.get_height() + 6))

    # ── Wave ──
    def _draw_wave(self, surface: pygame.Surface) -> None:
        cx = S.Window.WIDTH // 2
        y = self.PADDING + 4

        font = self._get_font(S.FontCfg.LARGE, bold=True)
        text = f"WAVE {self.wave:02d}"

        # اعمال scale
        # Apply scale
        # متن ابتدا در اندازه‌ی پایه رندر می‌شود تا ابعاد نسخه‌ی بزرگ‌شده از روی آن محاسبه شود.
        # Renders the text at its base size first so the enlarged dimensions can be calculated from it.
        img = font.render(text, True, S.Palette.WHITE)
        base_w, base_h = img.get_size()
        scale = self.wave_display_scale
        w = int(base_w * scale)
        h = int(base_h * scale)
        img_scaled = pygame.transform.smoothscale(img, (w, h))

        rect = img_scaled.get_rect(center=(cx, y + h // 2))

        # هاله/فلاش روی تغییر موج
        # Halo/flash when the wave changes
        # نسخه‌ی بزرگ‌تر متن با ترکیب افزایشی رسم می‌شود تا هنگام تغییر موج جلوه‌ی درخشان ایجاد کند.
        # Draws an enlarged text copy with additive blending to create a glow effect when the wave changes.
        if self.wave_change_flash > 0.01:
            flash_img = pygame.transform.smoothscale(
                img, (int(w * 1.25), int(h * 1.25))
            )
            flash_surf = pygame.Surface(flash_img.get_size(), pygame.SRCALPHA)
            flash_surf.blit(flash_img, (0, 0))
            flash_surf.set_alpha(int(80 * self.wave_change_flash))
            surface.blit(
                flash_surf,
                flash_surf.get_rect(center=rect.center),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

        surface.blit(img_scaled, rect)

        # خط تزئینی زیر شماره موج
        # Decorative line beneath the wave number
        line_w = 90
        line_y = y + h + 6
        a = 180
        pygame.draw.line(
            surface, (*S.Palette.HUD_ACCENT, a),
            (cx - line_w // 2, line_y),
            (cx + line_w // 2, line_y),
            1,
        )

    # ── قلب‌های جان ──
    def _draw_hearts(self, surface: pygame.Surface) -> None:
        if not self._hearts:
            return

        # اندازه و فاصله‌ی قلب‌ها برای محاسبه‌ی عرض کل ردیف استفاده می‌شوند.
        # Heart size and spacing are used to calculate the total width of the row.
        size = 26
        gap = 10
        total_w = len(self._hearts) * size + (len(self._hearts) - 1) * gap
        x0 = S.Window.WIDTH - self.PADDING - total_w
        y = self.PADDING + 4

        for i, h in enumerate(self._hearts):
            x = x0 + i * (size + gap)
            cx = x + size // 2
            cy = y + size // 2

            # پالس برای قلب‌های پر
            # Pulse for filled hearts
            # قلب‌های پر، در صورت نداشتن انیمیشن بازیابی، با موج سینوسی کمی تغییر اندازه می‌دهند.
            # Filled hearts gently change size with a sine wave when no restoration animation is active.
            pulse = 1.0
            if h.filled and h.pop_t <= 0.0:
                pulse = 1.0 + 0.08 * math.sin(self._t * 3.5 + i * 0.4)

            if h.burst_t > 0.0 and not h.filled:
                # انیمیشن ترکیدن
                # Burst animation
                # قلب ازدست‌رفته هم‌زمان بزرگ‌تر و شفاف‌تر می‌شود تا به‌تدریج محو شود.
                # The lost heart grows and becomes more transparent as it gradually fades out.
                t = h.burst_t
                scale = 1.0 + t * 0.9
                alpha = int(255 * (1.0 - t))
                self._draw_heart(
                    surface, cx, cy, int(size * scale * 0.5),
                    (*S.Palette.HUD_HP, alpha), filled=True, glowed=True,
                )
            elif h.filled:
                # هنگام بازیابی جان، افزایش مقیاس به‌صورت موقت روی اندازه‌ی عادی اعمال می‌شود.
                # During health restoration, a temporary scale increase is applied to the normal size.
                scale = pulse * (1.0 + (h.pop_t * 0.4 if 0.0 < h.pop_t < 1.0 else 0.0))
                self._draw_heart(
                    surface, cx, cy, int(size * 0.5 * scale),
                    S.Palette.HUD_HP, filled=True, glowed=True,
                )
            else:
                # قلب خالی — فقط خط دور
                # Empty heart — outline only
                self._draw_heart(
                    surface, cx, cy, int(size * 0.5),
                    (60, 30, 30), filled=False, glowed=False,
                )

    def _draw_heart(
        self,
        surface: pygame.Surface,
        cx: float, cy: float,
        r: int,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        *,
        filled: bool,
        glowed: bool,
    ) -> None:
        """رسم یک قلب از دو دایره + یک مثلث."""
        # اگر color آلفا دارد، روی سطح موقت بکش
        # If color includes alpha, draw onto a temporary surface.
        # سطح موقت امکان ترکیب رنگ نیمه‌شفاف قلب با سطح اصلی را فراهم می‌کند.
        # The temporary surface allows the semi-transparent heart color to blend with the main surface.
        has_alpha = len(color) == 4

        if has_alpha:
            size = r * 4
            tmp = pygame.Surface((size, size), pygame.SRCALPHA)
            local_cx = local_cy = size // 2
            self._draw_heart_shape(tmp, local_cx, local_cy, r, color, filled=filled)
            surface.blit(tmp, (cx - local_cx, cy - local_cy))
            return

        self._draw_heart_shape(surface, cx, cy, r, color, filled=filled)

    def _draw_heart_shape(
        self,
        surface: pygame.Surface,
        cx: float, cy: float,
        r: int,
        color: tuple[int, int, int] | tuple[int, int, int, int],
        *,
        filled: bool,
    ) -> None:
        # دو دایره + یک مثلث
        # Two circles + one triangle
        # دو دایره‌ی بالایی و مثلث پایینی با هم شکل قلب را تشکیل می‌دهند.
        # The two upper circles and the lower triangle combine to form the heart shape.
        offset = r // 2
        pygame.draw.circle(surface, color, (int(cx - offset), int(cy - offset // 2)), r // 2 + 1)
        pygame.draw.circle(surface, color, (int(cx + offset), int(cy - offset // 2)), r // 2 + 1)
        pts = [
            (cx - r + 1, cy - offset // 2 + 2),
            (cx + r - 1, cy - offset // 2 + 2),
            (cx, cy + r),
        ]
        pygame.draw.polygon(surface, color, pts)
        if not filled:
            # قلب خالی — یک دایره‌ی کوچک سیاه روی مرکز برای حس خالی بودن
            pass

    # ── نوار Power-Up ──
    def _draw_powerup(self, surface: pygame.Surface) -> None:
        if self.powerup_ratio <= 0.01:
            return

        x = self.PADDING
        y = S.Window.HEIGHT - self.PADDING - self.BAR_HEIGHT - 18

        # برچسب
        # Label
        label_font = self._get_font(S.FontCfg.TINY, bold=True)
        label = label_font.render("POWER", True, self.powerup_color)
        surface.blit(label, (x, y - 4))

        # پس‌زمینه‌ی نوار
        # Bar background
        bg_rect = pygame.Rect(x, y + 12, self.BAR_WIDTH, self.BAR_HEIGHT)
        pygame.draw.rect(surface, (10, 15, 25), bg_rect, border_radius=3)

        # نوار پر — رنگ بر اساس نسبت
        # Filled bar — color based on remaining ratio
        w = int(self.BAR_WIDTH * self.powerup_ratio)
        if w > 0:
            # رنگ نوار با کم شدن، به قرمز می‌رود
            # The bar color shifts toward red as the remaining ratio decreases.
            t = self.powerup_ratio
            r = int(255 * (1 - t) + self.powerup_color[0] * t)
            g = int(60 * (1 - t) + self.powerup_color[1] * t)
            b = int(60 * (1 - t) + self.powerup_color[2] * t)
            bar_color = (r, g, b)

            # پالس ملایم اگر نزدیک پایان است
            # Gentle pulse when nearly depleted
            # نزدیک پایان پاورآپ، شدت رنگ با تابع سینوسی نوسان می‌کند تا کاهش زمان باقی‌مانده جلب توجه کند.
            # Near depletion, the color intensity oscillates sinusoidally to draw attention to the remaining time.
            if self.powerup_ratio < 0.25:
                pulse = 0.7 + 0.3 * math.sin(self._t * 12.0)
                bar_color = tuple(int(c * pulse) for c in bar_color)
            bar_rect = pygame.Rect(x, y + 12, w, self.BAR_HEIGHT)
            pygame.draw.rect(surface, bar_color, bar_rect, border_radius=3)

        # حاشیه‌ی درخشان
        # Glowing border
        pygame.draw.rect(surface, self.powerup_color, bg_rect, 1, border_radius=3)

    # ── Combo ──
    def _draw_combo(self, surface: pygame.Surface) -> None:
        if self.combo < 2:
            return

        cx = S.Window.WIDTH // 2
        y = S.Window.HEIGHT - 140  # کمی بالاتر از قبل

        # ---- رنگ بر اساس مقدار combo ----
        # Color based on combo count
        # با افزایش تعداد Combo، رنگ متن از زرد به نارنجی، قرمز و سپس صورتی تغییر می‌کند.
        # As the combo count increases, the text color changes from yellow to orange, red, and then pink.
        if self.combo >= 30:
            color = (255, 80, 200)      # صورتی جیغ
        elif self.combo >= 20:
            color = (255, 60, 60)       # قرمز آتشین
        elif self.combo >= 10:
            color = (255, 180, 40)      # نارنجی طلایی
        else:
            color = (255, 240, 80)      # زرد روشن

        # ---- متن ----
        # Text
        text = f"{self.combo}x COMBO"
        font = self._get_font(S.FontCfg.LARGE, bold=True)
        img = font.render(text, True, color)

        # اعمال scale
        # Apply scale
        # ابعاد متن با مقیاس فعلی Combo تنظیم می‌شود و حداقل یک پیکسل برای هر بُعد حفظ می‌شود.
        # Scales the text dimensions using the current combo scale while keeping each dimension at least one pixel.
        w = max(1, int(img.get_width() * self.combo_scale))
        h = max(1, int(img.get_height() * self.combo_scale))
        img_scaled = pygame.transform.smoothscale(img, (w, h))
        rect = img_scaled.get_rect(center=(cx, y))

        # ---- پس‌زمینه‌ی شیشه‌ای (مهم‌ترین بخش برای خوانایی) ----
        # ---- Glass-like background (the most important part for readability) ----
        pad_x = 24
        pad_y = 10
        bg_rect = pygame.Rect(
            rect.x - pad_x,
            rect.y - pad_y,
            rect.width + pad_x * 2,
            rect.height + pad_y * 2,
        )

        # گرادیان ملایم در پس‌زمینه
        # Subtle background gradient
        bg = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg, (10, 15, 30, 200), bg.get_rect(), border_radius=12)
        surface.blit(bg, bg_rect.topleft)

        # حاشیه‌ی درخشان
        # Glowing border
        border = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            border, (*color, 180),
            border.get_rect(), 2, border_radius=12,
        )
        surface.blit(border, bg_rect.topleft)

        # ---- درخشش نرم پشت متن ----
        # ---- Soft glow behind the text ----
        # هاله از چند دایره با شعاع و آلفای متفاوت ساخته می‌شود تا درخشش تدریجی ایجاد کند.
        # Builds the halo from multiple circles with different radii and alpha values to create a gradual glow.
        glow_r = 40
        halo = pygame.Surface((w + glow_r * 2, h + glow_r * 2), pygame.SRCALPHA)
        for rr in range(glow_r, 0, -4):
            a = int(50 * (1 - rr / glow_r) ** 2)
            if a <= 0:
                continue
            pygame.draw.circle(halo, (*color, a), (w // 2 + glow_r, h // 2 + glow_r), rr)
        surface.blit(
            halo, (rect.x - glow_r, rect.y - glow_r),
            special_flags=pygame.BLEND_RGBA_ADD,
        )

        # ---- خط دور متن (Outline) برای خوانایی صد در صد ----
        # ---- Text outline for maximum readability ----
        # متن مشکی در هشت جهت اطراف نوشته‌ی اصلی رسم می‌شود تا مرز آن از پس‌زمینه جدا بماند.
        # Draws black text in eight directions around the main text to separate it from the background.
        outline_color = (0, 0, 0)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, 2), (-2, 2), (2, -2)]:
            shadow = font.render(text, True, outline_color)
            w2 = max(1, int(shadow.get_width() * self.combo_scale))
            h2 = max(1, int(shadow.get_height() * self.combo_scale))
            shadow_scaled = pygame.transform.smoothscale(shadow, (w2, h2))
            surface.blit(shadow_scaled, (rect.x + dx, rect.y + dy))

        # ---- متن اصلی ----
        # ---- Main text ----
        surface.blit(img_scaled, rect)

        # ---- نوار زمان Combo در زیر باکس ----
        # ---- Combo timer bar beneath the panel ----
        # نسبت زمان باقی‌مانده به زمان مجاز، طول بخش پرشده‌ی نوار را تعیین می‌کند.
        # The ratio of remaining time to the allowed duration determines the filled bar width.
        ratio = max(0.0, self.combo_timer / self.combo_max_time) if self.combo_max_time > 0 else 0.0
        bar_w = bg_rect.width - 20
        bar_h = 4
        bar_x = bg_rect.x + 10
        bar_y = bg_rect.bottom - 2

        # پس‌زمینه‌ی نوار
        # Bar background
        pygame.draw.rect(surface, (30, 30, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
        # نوار پر شده
        # Filled bar
        pygame.draw.rect(surface, color, (bar_x, bar_y, int(bar_w * ratio), bar_h), border_radius=2)

    # ── متن‌های شناور ──
    def _draw_floaters(self, surface: pygame.Surface) -> None:
        for f in self.floaters:
            # زمان سپری‌شده به نسبت کل عمر پیام تبدیل می‌شود و مبنای محاسبه‌ی شفافیت قرار می‌گیرد.
            # Converts elapsed lifetime into a normalized progress value used to calculate transparency.
            t = 1.0 - (f.life / f.max_life)  # 0 → 1
            alpha = int(255 * (1.0 - t * t))  # محو نمایی
            if alpha <= 0:
                continue

            font = self._get_font(f.font_size, bold=True)
            img = font.render(f.text, True, f.color)

            # scale
            # Scale
            # در صورت تغییر مقیاس، متن با ابعاد جدید و با حفظ حداقل اندازه‌ی یک پیکسل بازنمونه‌برداری می‌شود.
            # When scaled, the text is resampled to the new dimensions while preserving a minimum size of one pixel.
            if f.scale != 1.0:
                w = max(1, int(img.get_width() * f.scale))
                h = max(1, int(img.get_height() * f.scale))
                img = pygame.transform.smoothscale(img, (w, h))

            img.set_alpha(alpha)
            rect = img.get_rect(center=(int(f.x), int(f.y)))
            surface.blit(img, rect)

    # ── FPS ──
    def _draw_fps(self, surface: pygame.Surface) -> None:
        font = self._get_font(S.FontCfg.TINY, bold=True)
        text = f"{self.fps:5.1f} FPS"
        img = font.render(text, True, S.Palette.HUD_ACCENT)
        rect = img.get_rect()
        rect.topright = (S.Window.WIDTH - self.PADDING, S.Window.HEIGHT - 22)

        # پس‌زمینه‌ی نیمه‌شفاف، خوانایی مقدار FPS را روی صحنه افزایش می‌دهد.
        # A semi-transparent background improves FPS text readability over the game scene.
        bg = pygame.Surface((rect.width + 8, rect.height + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        surface.blit(bg, (rect.x - 4, rect.y - 2))
        surface.blit(img, rect)


    def _draw_text_glow(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        pos: tuple[int, int],
        color: tuple[int, int, int],
        *,
        glow: int = 1,
    ) -> None:
        # متن در چهار جهت اطراف موقعیت اصلی رسم می‌شود تا جلوه‌ی درخشش ایجاد شود.
        # Draws the text in four directions around its original position to create a glow effect.
        base = font.render(text, True, color)
        for dx, dy in ((-glow, 0), (glow, 0), (0, -glow), (0, glow)):
            surface.blit(base, (pos[0] + dx, pos[1] + dy), special_flags=pygame.BLEND_RGBA_ADD)


    def reset(self) -> None:
        """بازنشانی کامل برای شروع بازی جدید."""
        # تمام مقادیر وابسته به وضعیت بازی و انیمیشن‌ها به حالت اولیه بازمی‌گردند.
        # Resets all game-state values and animation properties to their initial state.
        self.score = 0
        self.score_display = 0.0
        self.hp = 0
        self.max_hp = 0
        self._hearts = []
        self.wave = 0
        self.wave_display_scale = 1.0
        self.wave_change_flash = 0.0
        self.powerup_ratio = 0.0
        self.combo = 0
        self.combo_timer = 0.0
        self.floaters.clear()
        self._damage_flash = 0.0


__all__ = ["HUD"]
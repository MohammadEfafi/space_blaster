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


# ═══════════════════════════════════════════════════════════════════════════
#  مدل‌های داده
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
#  کلاس HUD
# ═══════════════════════════════════════════════════════════════════════════

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

    # ─────────────────────────────────────────────────────────────────────
    #  فونت
    # ─────────────────────────────────────────────────────────────────────

    def _get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        cache = self._font_bold_cache if bold else self._font_cache
        font = cache.get(size)
        if font is None:
            font = pygame.font.SysFont(S.FontCfg.FAMILY, size, bold=bold)
            cache[size] = font
        return font

    # ─────────────────────────────────────────────────────────────────────
    #  API عمومی — تنظیم مقادیر
    # ─────────────────────────────────────────────────────────────────────

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
        if max_hp is not None and max_hp != self.max_hp:
            self.max_hp = max_hp
            self._hearts = [_HeartState(filled=True) for _ in range(max_hp)]

        old_hp = self.hp
        self.hp = max(0, int(hp))

        # اگر قلب از دست رفت → انیمیشن ترکیدن
        if self.hp < old_hp and self.hp < len(self._hearts):
            for i in range(self.hp, min(old_hp, len(self._hearts))):
                self._hearts[i].filled = False
                self._hearts[i].burst_t = 0.0001
            self._damage_flash = 0.6

        # اگر قلب اضافه شد → پاپ
        elif self.hp > old_hp:
            for i in range(old_hp, min(self.hp, len(self._hearts))):
                self._hearts[i].filled = True
                self._hearts[i].pop_t = 0.0001

    def set_wave(self, wave: int) -> None:
        if wave != self.wave:
            self.wave = int(wave)
            self.wave_display_scale = 1.5
            self.wave_change_flash = 0.6

    def set_powerup(self, ratio: float, color: Optional[tuple[int, int, int]] = None) -> None:
        """نسبت باقی‌مانده‌ی پاورآپ (0..1) و رنگ (اختیاری)."""
        self.powerup_ratio = max(0.0, min(1.0, ratio))
        if color is not None:
            self.powerup_color = color

    def set_fps(self, fps: float) -> None:
        self.fps = fps

    def set_show_fps(self, show: bool) -> None:
        self._show_fps = show

    # ─────────────────────────────────────────────────────────────────────
    #  Combo
    # ─────────────────────────────────────────────────────────────────────

    def register_kill(self, combo_value: int = 1) -> None:
        """هر بار دشمن کشته شد، Combo را افزایش می‌ده."""
        self.combo += combo_value
        self.combo_timer = self.combo_max_time
        self.combo_scale = 1.4

    def reset_combo(self) -> None:
        self.combo = 0
        self.combo_timer = 0.0

    # ─────────────────────────────────────────────────────────────────────
    #  متن شناور
    # ─────────────────────────────────────────────────────────────────────

    def notify_score(
        self,
        amount: int,
        x: float, y: float,
        *,
        color: Optional[tuple[int, int, int]] = None,
        prefix: str = "+",
    ) -> None:
        """نمایش «+۵۰» روی موقعیت مشخص."""
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

    # ─────────────────────────────────────────────────────────────────────
    #  به‌روزرسانی
    # ─────────────────────────────────────────────────────────────────────

    def update(self, dt: float) -> None:
        self._t += dt

        # ---- امتیاز نرم ----
        diff = self.score - self.score_display
        if abs(diff) < 0.5:
            self.score_display = float(self.score)
        else:
            # میل نمایی — سریع در ابتدا، آرام در انتها
            self.score_display += diff * min(1.0, dt * 8.0)

        # ---- فلاش موج ----
        if self.wave_change_flash > 0.0:
            self.wave_change_flash = max(0.0, self.wave_change_flash - dt * 2.0)
        if self.wave_display_scale > 1.0:
            self.wave_display_scale = max(1.0, self.wave_display_scale - dt * 2.0)

        # ---- Combo ----
        if self.combo_timer > 0.0:
            self.combo_timer -= dt
            if self.combo_timer <= 0.0:
                self.combo = 0
        if self.combo_scale > 1.0:
            self.combo_scale = max(1.0, self.combo_scale - dt * 4.0)

        # ---- فلاش قرمز ضربه ----
        if self._damage_flash > 0.0:
            self._damage_flash = max(0.0, self._damage_flash - dt * 1.5)

        # ---- قلب‌ها ----
        for h in self._hearts:
            if h.burst_t > 0.0 and h.burst_t < 1.0:
                h.burst_t = min(1.0, h.burst_t + dt * 3.5)
            if h.pop_t > 0.0 and h.pop_t < 1.0:
                h.pop_t = min(1.0, h.pop_t + dt * 4.0)

        # ---- متن‌های شناور ----
        alive_floaters: list[_FloatingText] = []
        for f in self.floaters:
            f.life -= dt
            if f.life <= 0.0:
                continue
            f.y += f.vy * dt
            f.vy *= (1.0 - dt * 2.2)
            if f.scale_vel != 0.0:
                f.scale += f.scale_vel * dt
                if f.scale < 1.0:
                    f.scale = 1.0
                    f.scale_vel = 0.0
            alive_floaters.append(f)
        self.floaters = alive_floaters

    # ─────────────────────────────────────────────────────────────────────
    #  رندر
    # ─────────────────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

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
        a = int(140 * self._damage_flash)
        w, h = surface.get_size()
        # از گوشه‌ها به مرکز — گرادیان شعاعی ساده با چند لایه
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        thickness = 80
        for i in range(thickness):
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
        label = self._get_font(S.FontCfg.SMALL, bold=True)
        img_label = label.render("SCORE", True, S.Palette.HUD_ACCENT)
        surface.blit(img_label, (x, y))

        # مقدار
        font = self._get_font(S.FontCfg.LARGE, bold=True)
        text = f"{int(self.score_display):,}"
        img = font.render(text, True, S.Palette.WHITE)
        surface.blit(img, (x, y + img_label.get_height() + 2))

        # High Score (زیر امتیاز جاری)
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
        img = font.render(text, True, S.Palette.WHITE)
        base_w, base_h = img.get_size()
        scale = self.wave_display_scale
        w = int(base_w * scale)
        h = int(base_h * scale)
        img_scaled = pygame.transform.smoothscale(img, (w, h))

        rect = img_scaled.get_rect(center=(cx, y + h // 2))

        # هاله/فلاش روی تغییر موج
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
            pulse = 1.0
            if h.filled and h.pop_t <= 0.0:
                pulse = 1.0 + 0.08 * math.sin(self._t * 3.5 + i * 0.4)

            if h.burst_t > 0.0 and not h.filled:
                # انیمیشن ترکیدن
                t = h.burst_t
                scale = 1.0 + t * 0.9
                alpha = int(255 * (1.0 - t))
                self._draw_heart(
                    surface, cx, cy, int(size * scale * 0.5),
                    (*S.Palette.HUD_HP, alpha), filled=True, glowed=True,
                )
            elif h.filled:
                scale = pulse * (1.0 + (h.pop_t * 0.4 if 0.0 < h.pop_t < 1.0 else 0.0))
                self._draw_heart(
                    surface, cx, cy, int(size * 0.5 * scale),
                    S.Palette.HUD_HP, filled=True, glowed=True,
                )
            else:
                # قلب خالی — فقط خط دور
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
        label_font = self._get_font(S.FontCfg.TINY, bold=True)
        label = label_font.render("POWER", True, self.powerup_color)
        surface.blit(label, (x, y - 4))

        # پس‌زمینه‌ی نوار
        bg_rect = pygame.Rect(x, y + 12, self.BAR_WIDTH, self.BAR_HEIGHT)
        pygame.draw.rect(surface, (10, 15, 25), bg_rect, border_radius=3)

        # نوار پر — رنگ بر اساس نسبت
        w = int(self.BAR_WIDTH * self.powerup_ratio)
        if w > 0:
            # رنگ نوار با کم شدن، به قرمز می‌رود
            t = self.powerup_ratio
            r = int(255 * (1 - t) + self.powerup_color[0] * t)
            g = int(60 * (1 - t) + self.powerup_color[1] * t)
            b = int(60 * (1 - t) + self.powerup_color[2] * t)
            bar_color = (r, g, b)
            # پالس ملایم اگر نزدیک پایان است
            if self.powerup_ratio < 0.25:
                pulse = 0.7 + 0.3 * math.sin(self._t * 12.0)
                bar_color = tuple(int(c * pulse) for c in bar_color)
            bar_rect = pygame.Rect(x, y + 12, w, self.BAR_HEIGHT)
            pygame.draw.rect(surface, bar_color, bar_rect, border_radius=3)

        # حاشیه‌ی درخشان
        pygame.draw.rect(surface, self.powerup_color, bg_rect, 1, border_radius=3)

    # ── Combo ──
    def _draw_combo(self, surface: pygame.Surface) -> None:
        if self.combo < 2:
            return

        cx = S.Window.WIDTH // 2
        y = S.Window.HEIGHT - 110

        # رنگ بر اساس مقدار combo
        if self.combo >= 20:
            color = S.Palette.PINK
        elif self.combo >= 10:
            color = S.Palette.YELLOW
        else:
            color = S.Palette.HUD_ACCENT

        font = self._get_font(S.FontCfg.LARGE, bold=True)
        text = f"{self.combo}x COMBO"

        # scale انیمیشن
        img = font.render(text, True, color)
        w = int(img.get_width() * self.combo_scale)
        h = int(img.get_height() * self.combo_scale)
        if w > 0 and h > 0:
            img_scaled = pygame.transform.smoothscale(img, (w, h))
            rect = img_scaled.get_rect(center=(cx, y))

            # هاله‌ی رنگی
            glow = pygame.transform.smoothscale(img, (int(w * 1.15), int(h * 1.15)))
            gs = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
            gs.blit(glow, (0, 0))
            gs.set_alpha(80)
            surface.blit(
                gs, gs.get_rect(center=rect.center),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

            surface.blit(img_scaled, rect)

        # نوار زمان combo
        ratio = max(0.0, self.combo_timer / self.combo_max_time) if self.combo_max_time > 0 else 0.0
        bar_w = 120
        bar_h = 3
        bar_x = cx - bar_w // 2
        bar_y = y + 24
        pygame.draw.rect(surface, (30, 30, 50), (bar_x, bar_y, bar_w, bar_h))
        pygame.draw.rect(surface, color, (bar_x, bar_y, int(bar_w * ratio), bar_h))

    # ── متن‌های شناور ──
    def _draw_floaters(self, surface: pygame.Surface) -> None:
        for f in self.floaters:
            t = 1.0 - (f.life / f.max_life)  # 0 → 1
            alpha = int(255 * (1.0 - t * t))  # محو نمایی
            if alpha <= 0:
                continue
            font = self._get_font(f.font_size, bold=True)
            img = font.render(f.text, True, f.color)

            # scale
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
        bg = pygame.Surface((rect.width + 8, rect.height + 4), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        surface.blit(bg, (rect.x - 4, rect.y - 2))
        surface.blit(img, rect)

    # ─────────────────────────────────────────────────────────────────────
    #  کمکی: هاله‌ی متن
    # ─────────────────────────────────────────────────────────────────────

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
        base = font.render(text, True, color)
        for dx, dy in ((-glow, 0), (glow, 0), (0, -glow), (0, glow)):
            surface.blit(base, (pos[0] + dx, pos[1] + dy), special_flags=pygame.BLEND_RGBA_ADD)

    # ─────────────────────────────────────────────────────────────────────
    #  ریست
    # ─────────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        """بازنشانی کامل برای شروع بازی جدید."""
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